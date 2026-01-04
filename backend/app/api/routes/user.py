import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db_session
from app.core.redis import get_redis
from app.core.settings import get_settings
from app.dependencies.auth import CurrentUser, get_current_user
from app.models.user import User
from app.schema.base import ApiResult
from app.schema.user import (
    ChangePasswordPayload,
    UserLoginPayload,
    UserParamPayload,
    UserUpdatePayload,
    UserVo,
)
from app.services.auth_service import AuthService
from app.utils.alioss_util import get_oss_client
from app.utils.session_store import SessionStore

router = APIRouter(prefix="/user", tags=["用户"])


@router.post("/register", response_model=ApiResult[int])
async def register_user(
    payload: UserParamPayload,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
):
    """
    1. 用户注册：校验重复，写入 bcrypt 哈希。
    """
    settings = get_settings()
    store = SessionStore(redis, settings)
    service = AuthService(db, store, settings)
    try:
        # 1. 执行注册并返回主键
        user_id = await service.register(payload.model_dump())
        return ApiResult.ok(user_id)
    except ValueError as ex:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return ApiResult.error("USER-400", str(ex))


@router.post("/update", response_model=ApiResult[UserVo])
async def update_user(
    payload: UserParamPayload,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
):
    """
    1. 用户信息修改：目前仅更新基本资料，密码修改单独接口
    """
    # 1. 读取用户并更新基础字段
    user: User | None = await db.get(User, current.id)
    if user is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return ApiResult.error("USER-404", "用户不存在")
    user.user_name = payload.userName or user.user_name
    user.user_phone = payload.userPhone or user.user_phone
    user.address = payload.address or user.address
    user.user_sex = payload.userSex if payload.userSex is not None else user.user_sex
    await db.commit()
    await db.refresh(user)
    vo = UserVo(
        userCode=user.user_code,
        userName=user.user_name,
        userSex=user.user_sex,
        userPhone=user.user_phone,
        address=user.address,
        maxLoginNum=user.max_login_num,
        avatar=user.avatar,
    )
    return ApiResult.ok(vo)


@router.post("/login", response_model=ApiResult[str])
async def login_user(
    payload: UserLoginPayload,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis=Depends(get_redis),
):
    """
    用户登录：验证凭据，生成 JWT 并写入 Redis 会话。

    Token 通过响应体返回，前端存储到 localStorage 并在请求时通过 Header 发送。
    """
    settings = get_settings()
    store = SessionStore(redis, settings)
    service = AuthService(db, store, settings)
    try:
        token = await service.login(payload.model_dump())
        return ApiResult.ok(token)
    except ValueError as ex:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return ApiResult.error("USER-401", str(ex))


@router.post("/logout", response_model=ApiResult[None])
async def logout_user(
    current: CurrentUser = Depends(get_current_user),
    redis=Depends(get_redis),
):
    """
    注销：删除 Redis 会话
    """
    settings = get_settings()
    store = SessionStore(redis, settings)
    await store.remove_session(str(current.id), current.token)
    return ApiResult.ok()


@router.get("/me", response_model=ApiResult[UserVo])
async def get_current_user_info(
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
):
    """
    1. 获取当前登录用户信息，无需传入 user_id。
    """
    user: User | None = await db.get(User, current.id)
    if user is None:
        raise ValueError("用户不存在")
    vo = UserVo(
        userCode=user.user_code,
        userName=user.user_name,
        userSex=user.user_sex,
        userPhone=user.user_phone,
        address=user.address,
        maxLoginNum=user.max_login_num,
        avatar=user.avatar,
    )
    return ApiResult.ok(vo)


@router.get("/detail/{user_id}", response_model=ApiResult[UserVo])
async def get_user_detail(
    user_id: int,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
):
    """
    1. 查询用户详情：仅允许本人查询。
    """
    # 1. 校验用户存在与归属
    user: User | None = await db.get(User, user_id)
    if user is None:
        response.status_code = status.HTTP_404_NOT_FOUND
        return ApiResult.error("USER-404", "用户不存在")
    if current.id != user.id:
        response.status_code = status.HTTP_403_FORBIDDEN
        return ApiResult.error("USER-403", "无权查看其他用户信息")
    vo = UserVo(
        userCode=user.user_code,
        userName=user.user_name,
        userSex=user.user_sex,
        userPhone=user.user_phone,
        address=user.address,
        maxLoginNum=user.max_login_num,
        avatar=user.avatar,
    )
    return ApiResult.ok(vo)


# 允许的图片类型
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/upload/avatar", response_model=ApiResult[str])
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[str]:
    """
    上传用户头像到 OSS

    - 仅支持 JPEG, PNG, GIF, WebP 格式
    - 文件大小限制 5MB
    - 返回头像访问 URL
    """
    # 1. 验证文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        return ApiResult.error(
            "UPLOAD-400",
            f"不支持的文件类型: {file.content_type}，仅支持 JPEG/PNG/GIF/WebP",
        )

    # 2. 读取文件内容并验证大小
    contents = await file.read()
    file_size = len(contents)

    if file_size == 0:
        return ApiResult.error("UPLOAD-400", "文件内容为空")

    if file_size > MAX_FILE_SIZE:
        return ApiResult.error("UPLOAD-400", "文件大小超过 5MB 限制")

    # 3. 生成唯一文件名
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    key = f"avatars/{current.id}/{uuid.uuid4().hex}.{ext}"

    # 4. 上传到 OSS
    from loguru import logger

    logger.info(f"[upload_avatar] 准备上传: size={file_size}, key={key}")

    oss = get_oss_client()
    result = oss.upload_bytes(contents, key, content_type=file.content_type)

    if not result["success"]:
        return ApiResult.error("UPLOAD-500", "上传失败，请稍后重试")

    avatar_url = result["url"]

    # 5. 更新用户头像字段
    user: User | None = await db.get(User, current.id)
    if user:
        user.avatar = avatar_url
        await db.commit()

    return ApiResult.ok(avatar_url)


@router.post("/update-profile", response_model=ApiResult[UserVo])
async def update_profile(
    payload: UserUpdatePayload,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[UserVo]:
    """
    更新用户基本资料（不含密码）
    """
    user: User | None = await db.get(User, current.id)
    if user is None:
        return ApiResult.error("USER-404", "用户不存在")

    # 只更新非空字段
    if payload.userName is not None:
        user.user_name = payload.userName
    if payload.userPhone is not None:
        user.user_phone = payload.userPhone
    if payload.address is not None:
        user.address = payload.address
    if payload.userSex is not None:
        user.user_sex = payload.userSex

    await db.commit()
    await db.refresh(user)

    vo = UserVo(
        userCode=user.user_code,
        userName=user.user_name,
        userSex=user.user_sex,
        userPhone=user.user_phone,
        address=user.address,
        maxLoginNum=user.max_login_num,
        avatar=user.avatar,
    )
    return ApiResult.ok(vo)


@router.post("/change-password", response_model=ApiResult[None])
async def change_password(
    payload: ChangePasswordPayload,
    db: AsyncSession = Depends(get_db_session),
    current: CurrentUser = Depends(get_current_user),
) -> ApiResult[None]:
    """
    修改密码

    - 需要验证旧密码
    - 新密码至少 6 位
    """
    from app.utils.password import hash_password, verify_password

    user: User | None = await db.get(User, current.id)
    if user is None:
        return ApiResult.error("USER-404", "用户不存在")

    # 验证旧密码
    if not verify_password(payload.oldPassword, user.user_password):
        return ApiResult.error("USER-401", "旧密码不正确")

    # 更新密码
    user.user_password = hash_password(payload.newPassword)
    await db.commit()

    return ApiResult.ok()
