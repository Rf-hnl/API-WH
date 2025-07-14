from db import Base, engine

def init_db():
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas exitosamente!")

if __name__ == '__main__':
    init_db()
