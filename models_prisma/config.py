from prisma import Prisma
from .models import Tenant

prisma = Prisma()

try:
    prisma.connect()
except Exception as e:
    print(f"Error al conectar Prisma: {e}")
