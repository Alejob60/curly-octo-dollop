import logging
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.models.sql_models import Base, Dependency, PqrsType, Role, User

# Configuración de Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Usamos la URL de settings para mantener Clean Code
DATABASE_URL = settings.get_database_url

async def seed_database():
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL no está configurada en el entorno.")
        return

    engine = create_async_engine(DATABASE_URL)
    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    async with engine.begin() as conn:
        logger.info("Iniciando inyección de Master Data en PostgreSQL (Async)...")
        # Forzar recreación con CASCADE para limpiar dependencias de Misybot previo
        from sqlalchemy import text
        await conn.execute(text("DROP TABLE IF EXISTS radicados_legacy CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS asignaciones CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS trazabilidad CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS evidencias_bucket CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS radicados CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS dependencies CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS pqrs_types CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS roles CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
        
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        try:
            # 2. Limpieza previa y semillas de Dependencias Oficiales de Cali
            dependencias_cali = [
                {"id": 414501, "nombre": "SECRETARIA DE GOBIERNO", "es_activa": True},
                {"id": 414502, "nombre": "SECRETARIA DE SEGURIDAD Y JUSTICIA", "es_activa": True},
                {"id": 414503, "nombre": "SECRETARIA DE MOVILIDAD", "es_activa": True},
                {"id": 414504, "nombre": "DAGMA", "es_activa": True},
                {"id": 414505, "nombre": "SECRETARIA DE SALUD PUBLICA", "es_activa": True},
                {"id": 414506, "nombre": "SECRETARIA DE INFRAESTRUCTURA", "es_activa": True},
                {"id": 414507, "nombre": "SECRETARIA DE EDUCACION", "es_activa": True},
                {"id": 414508, "nombre": "SECRETARIA DE CULTURA", "es_activa": True},
                {"id": 414509, "nombre": "SECRETARIA DE HACIENDA", "es_activa": True},
                {"id": 414510, "nombre": "DEP. ADMINISTRATIVO DE PLANEACION", "es_activa": True}
            ]
            
            for dep in dependencias_cali:
                await db.merge(Dependency(**dep))

            # 3. Semillas de Tipos de PQRSD (Alineadas con Manual CDI/Orfeo)
            tipos_pqrsd = [
                {"codigo": "PET_GENERAL", "nombre": "Petición de Interés General", "dias_respuesta": 10},
                {"codigo": "PET_PARTICULAR", "nombre": "Petición de Interés Particular", "dias_respuesta": 10},
                {"codigo": "PET_INFORMACION", "nombre": "Petición de Informaciones", "dias_respuesta": 15},
                {"codigo": "CONSULTA", "nombre": "Derecho de Petición de Consultas", "dias_respuesta": 30},
                {"codigo": "QUEJA", "nombre": "Queja (Conducta Irregular)", "dias_respuesta": 15},
                {"codigo": "RECLAMO", "nombre": "Reclamo (Servicio Deficiente)", "dias_respuesta": 15},
                {"codigo": "DENUNCIA_CORR", "nombre": "Denuncia por actos de corrupción", "dias_respuesta": 15},
                {"codigo": "PET_AUTORIDAD", "nombre": "Petición entre autoridades", "dias_respuesta": 10}
            ]

            for idx, tipo in enumerate(tipos_pqrsd):
                await db.merge(PqrsType(id=idx+1, **tipo))

            # 4. Roles RBAC
            roles = [
                {"id": 1, "codigo": "CITIZEN", "nombre": "Ciudadano Digital", "nivel_acceso": 1},
                {"id": 2, "codigo": "FRONT_DESK", "nombre": "Operador de Ventanilla", "nivel_acceso": 2},
                {"id": 3, "codigo": "LAWYER", "nombre": "Abogado / Revisor Jurídico", "nivel_acceso": 3},
                {"id": 4, "codigo": "SECRETARY", "nombre": "Secretario de Despacho", "nivel_acceso": 4},
                {"id": 5, "codigo": "MAYOR", "nombre": "Alcalde / Gerencia de Ciudad", "nivel_acceso": 5}
            ]

            for role in roles:
                await db.merge(Role(**role))

            # 5. Funcionario de Prueba (Movilidad)
            test_lawyer = {
                "id": 101,
                "email": "juan.movilidad@cali.gov.co",
                "full_name": "Juan Pérez",
                "role_id": 3,
                "id_dependencia": 414503, # SECRETARIA DE MOVILIDAD
                "especialidad": "Fotomultas",
                "capacidad_maxima": 10,
                "carga_actual": 0,
                "is_available": True
            }
            await db.merge(User(**test_lawyer))

            # 6. Funcionaria Especialista (Seguridad y Justicia)
            expert_lawyer = {
                "id": 102,
                "email": "elena.santacruz@cali.gov.co",
                "full_name": "Dra. Elena Santacruz",
                "role_id": 3,
                "id_dependencia": 414502, # SEGURIDAD Y JUSTICIA
                "especialidad": "Inspección, Vigilancia y Control",
                "capacidad_maxima": 15,
                "carga_actual": 0,
                "is_available": True
            }
            await db.merge(User(**expert_lawyer))

            # 7. Funcionario Especialista (Hacienda)
            hacienda_lawyer = {
                "id": 103,
                "email": "roberto.fiscal@cali.gov.co",
                "full_name": "Dr. Roberto Fiscal",
                "role_id": 3,
                "id_dependencia": 414509, # HACIENDA
                "especialidad": "Estatuto Tributario / Impuesto Predial",
                "capacidad_maxima": 12,
                "carga_actual": 2,
                "is_available": True
            }
            await db.merge(User(**hacienda_lawyer))

            # 8. Funcionaria Especialista (Cultura / Patrimonio)
            culture_lawyer = {
                "id": 104,
                "email": "maria.patrimonio@cali.gov.co",
                "full_name": "Dra. Maria Patrimonio",
                "role_id": 3,
                "id_dependencia": 414508, # CULTURA
                "especialidad": "Patrimonio Arquitectónico / BIC",
                "capacidad_maxima": 10,
                "carga_actual": 1,
                "is_available": True
            }
            await db.merge(User(**culture_lawyer))

            # 9. Funcionario Especialista (DAGMA / Recurso Hídrico)
            dagma_lawyer = {
                "id": 105,
                "email": "tecnico.hidrico@cali.gov.co",
                "full_name": "Ing. Ricardo Aguas",
                "role_id": 3,
                "id_dependencia": 414504, # DAGMA
                "especialidad": "Recurso Hídrico",
                "capacidad_maxima": 10,
                "carga_actual": 0,
                "is_available": True
            }
            await db.merge(User(**dagma_lawyer))

            await db.commit()
            logger.info("✅ Master Data sembrada exitosamente en PostgreSQL. Orbital Prime está listo.")

        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Error inyectando semillas: {e}")
        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(seed_database())
