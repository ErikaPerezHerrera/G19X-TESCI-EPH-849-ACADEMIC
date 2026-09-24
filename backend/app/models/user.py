# Este código define el modelo ORM de SQLAlchemy para la entidad User (Usuarios).
# Es la entidad principal sobre la que giran la autenticación,
# la gestión de roles (recruiter, candidate, casual) y
# la propiedad de los CVs, ofertas de empleo y postulaciones en PluriJob.

import uuid

from sqlalchemy import Boolean, Column, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    """
    Modelo ORM que representa la tabla 'users'.
    Almacena la información de autenticación, perfil y rol de cada usuario
    (candidatos registrados, usuarios casuales/anónimos y reclutadores).
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_role", "role"),
        Index("idx_users_created_at", "created_at"),
    )

    # Identificador único de usuario (UUID v4)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Correo electrónico único para iniciar sesión
    email = Column(String(255), unique=True, nullable=False, index=True)

    # Contraseña encriptada con Bcrypt (nullable=True permite usuarios temporales/casuales sin contraseña)
    password_hash = Column(String(255), nullable=True)

    # Nombre completo del usuario o reclutador
    full_name = Column(String(150), nullable=True)

    # Rol del usuario en el sistema: 'casual', 'candidate' o 'recruiter'
    role = Column(
        ENUM(
            "casual",
            "registered",
            "recruiter",
            "admin",
            name="user_role_enum",
        ),
        nullable=False,
        default="casual",
        server_default="casual",
    )
    google_id = Column(String(255), unique=True, nullable=True)

    # Indica si la cuenta está activa (permite desactivar o banear usuarios sin borrar sus datos)
    is_active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Marcas de tiempo de creación y modificación administradas por PostgreSQL
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # --- RELACIONES DE ORM ---
    # CVs subidos por el usuario. Si el usuario se elimina, sus CVs se eliminan en cascada (cascade="all, delete-orphan")
    resumes = relationship(
        "Resume", back_populates="user", cascade="all, delete-orphan"
    )

    # Ofertas laborales publicadas si el usuario es un reclutador
    jobs = relationship("Job", back_populates="recruiter")

    # Historial de postulaciones realizadas por el usuario
    applications = relationship("Application", back_populates="user")
