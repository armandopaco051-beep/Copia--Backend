from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP
from app.database import Base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship



class Rol(Base) : 
    __tablename__ = "rol"
    __table_args__ = {'schema': 'seguridad'}
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, index=True)
    permisos = relationship("RolPermiso", back_populates="rol")
    usuarios = relationship("Usuario", back_populates="rol")

class Permiso(Base): 
    __tablename__ = "permiso"
    __table_args__= {"schema": "seguridad"}

    id= Column(Integer, primary_key=True, index=True)
    nombre= Column(String(100), nullable=False)
    roles =  relationship("RolPermiso", back_populates="permiso")

class RolPermiso(Base): 
    __tablename__ = "rol_permiso"
    __table_args__ = {"schema" :"seguridad"}

    id_rol = Column(Integer, ForeignKey("seguridad.rol.id", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    id_permiso = Column(Integer, ForeignKey("seguridad.permiso.id", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    rol = relationship("Rol", back_populates="permisos")
    permiso = relationship("Permiso", back_populates="roles")

class Usuario(Base):
    __tablename__ = "usuario"
    __table_args__ = {"schema": "seguridad"}
    
    codigo = Column(String(100), primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False)
    password = Column("contraseña", String(255), nullable=False)    
    telefono = Column(String(20), nullable=True)
    fecha_registro =Column(TIMESTAMP, server_default=func.now(), nullable=False)
    estado = Column(Boolean, default=True, nullable=False)
    id_rol = Column(Integer, ForeignKey("seguridad.rol.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    rol = relationship("Rol", back_populates="usuarios")
    vehiculos = relationship("Vehiculo", back_populates="usuario")



