"""
Automated script to create the initial super admin user.
Run this after database migrations to set up your admin account.
"""
import asyncio
from sqlalchemy import select
from app.database import async_session_maker
from app.models.user import User, UserRole, AuthProvider
from app.utils.auth import get_password_hash
from app.config import settings


async def create_super_admin():
    """Create or update the super admin user automatically."""
    
    async with async_session_maker() as session:
        # Check if super admin already exists
        stmt = select(User).where(User.email == settings.SUPER_ADMIN_EMAIL)
        result = await session.execute(stmt)
        admin_user = result.scalar_one_or_none()
        
        if admin_user:
            print(f"✓ Super admin user already exists: {admin_user.email}")
            print(f"  ID: {admin_user.id}")
            print(f"  Role: {admin_user.role.value}")
            print(f"  Active: {admin_user.is_active}")
            return
        
        # Create new super admin automatically
        print(f"\nCreating super admin user...")
        print(f"Email: {settings.SUPER_ADMIN_EMAIL}")
        print(f"Using password from .env configuration")
        
        admin_user = User(
            email=settings.SUPER_ADMIN_EMAIL,
            username="admin",
            full_name="Super Administrator",
            hashed_password=get_password_hash(settings.SUPER_ADMIN_PASSWORD),
            auth_provider=AuthProvider.LOCAL,
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True
        )
        
        session.add(admin_user)
        await session.commit()
        await session.refresh(admin_user)
        
        print(f"\n✅ Super admin created successfully!")
        print(f"   ID: {admin_user.id}")
        print(f"   Email: {admin_user.email}")
        print(f"   Username: {admin_user.username}")
        print(f"   Role: {admin_user.role.value}")
        print(f"\n⚠️  IMPORTANT: Change the default password after first login!")
        print(f"\n   Login credentials:")
        print(f"   Email: {admin_user.email}")
        print(f"   Password: {settings.SUPER_ADMIN_PASSWORD}")


if __name__ == "__main__":
    print("="*60)
    print("FileShield - Automated Super Admin Setup")
    print("="*60)
    asyncio.run(create_super_admin())
    print("="*60)
