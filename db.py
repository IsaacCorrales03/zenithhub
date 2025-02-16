import sqlite3

# Conectar a la base de datos (se crea automáticamente si no existe)
conn = sqlite3.connect('database.db')

# Crear un cursor para ejecutar comandos SQL
cursor = conn.cursor()

# Crear la tabla 'materias' si no existe (ahora con columna para el icono y recursos)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS materias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        icono TEXT NOT NULL,
        recursos INTEGER DEFAULT 0
    )
''')

# Crear la tabla 'profesores' si no existe (con referencia a materia_id)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS profesores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        materia_id INTEGER NOT NULL,
        email TEXT NOT NULL,
        FOREIGN KEY (materia_id) REFERENCES materias (id)
    )
''')

# Crear la tabla 'files' si no existe (con referencia a materia_id)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        materia_id INTEGER NOT NULL,
        profesor_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        filename TEXT NOT NULL,
        autor TEXT NOT NULL,
        extension TEXT NOT NULL,    
        FOREIGN KEY (materia_id) REFERENCES materias (id),
        FOREIGN KEY (profesor_id) REFERENCES profesores (id)
    )
''')

# Crear la tabla 'tareas' si no existe
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tareas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        fecha_vencimiento TEXT NOT NULL,
        profesor_id INTEGER NOT NULL,
        materia_id INTEGER NOT NULL,
        fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (profesor_id) REFERENCES profesores (id),
        FOREIGN KEY (materia_id) REFERENCES materias (id)
    )
''')

# Crear un trigger para actualizar automáticamente el conteo de recursos en la tabla 'materias'
cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS update_recursos_insert
    AFTER INSERT ON files
    BEGIN
        UPDATE materias
        SET recursos = recursos + 1
        WHERE id = NEW.materia_id;
    END;
''')

cursor.execute('''
    CREATE TRIGGER IF NOT EXISTS update_recursos_delete
    AFTER DELETE ON files
    BEGIN
        UPDATE materias
        SET recursos = recursos - 1
        WHERE id = OLD.materia_id;
    END;
''')

# Vaciar las tablas antes de insertar nuevos datos
cursor.execute('DELETE FROM files')
cursor.execute('DELETE FROM profesores')
cursor.execute('DELETE FROM materias')

# Lista de materias con sus iconos
materias_con_iconos = [
    ("Guía", "fas fa-compass text-purple-500 mr-3 text-2xl"),
    ("Educación Física", "fas fa-running text-green-500 mr-3 text-2xl"),
    ("Química", "fas fa-flask text-red-500 mr-3 text-2xl"),
    ("Emprendimiento", "fas fa-briefcase text-amber-500 mr-3 text-2xl"),
    ("CySaR", "fas fa-network-wired text-blue-500 mr-3 text-2xl"),
    ("Inglés Tec.", "fas fa-microchip text-gray-600 mr-3 text-2xl"),
    ("AySaC", "fas fa-server text-indigo-500 mr-3 text-2xl"),
    ("Música", "fas fa-music text-yellow-500 mr-3 text-2xl"),
    ("Cívica", "fas fa-landmark text-blue-700 mr-3 text-2xl"),
    ("Est. Sociales", "fas fa-globe-americas text-green-600 mr-3 text-2xl"),
    ("Español", "fas fa-book text-red-600 mr-3 text-2xl"),
    ("Psicología", "fas fa-brain text-pink-500 mr-3 text-2xl"),
    ("Ética", "fas fa-balance-scale text-teal-500 mr-3 text-2xl"),
    ("Inglés Acad.", "fas fa-language text-indigo-600 mr-3 text-2xl"),
    ("Matemática", "fas fa-calculator text-blue-500 mr-3 text-2xl"),
    ("Biología", "fas fa-dna text-green-500 mr-3 text-2xl")
]

# Insertar materias en la tabla
cursor.executemany('INSERT INTO materias (nombre, icono) VALUES (?, ?)', materias_con_iconos)

# Obtener el diccionario de materias para buscar IDs
cursor.execute('SELECT id, nombre FROM materias')
materias_dict = {nombre: id for id, nombre in cursor.fetchall()}

# Lista de profesores a insertar (ahora con materia_id en lugar de nombre de materia)
profesores = [
    ("Marta Ligía", materias_dict["Español"], "ligia.garcia.marengo@mep.go.cr"),
    ("Diego Vindas", materias_dict["Matemática"], "diego.vindas.esquivel@mep.go.cr"),
    ("Carlos Masis", materias_dict["CySaR"], "carlos.masis.navarro@mep.go.cr"),
    ("Yendry Solis", materias_dict["Est. Sociales"], "yendry.solis.moya@mep.go.cr"),
    ("Alejandro Jiménez", materias_dict["Cívica"], "alejandro.jimenez.murillo@mep.go.cr"),
    ("Elke Bruns", materias_dict["Biología"], "elke.bruns.coto@mep.go.cr"),
    ("Heleny Zugey", materias_dict["Química"], "helen.brenes.alvarez@mep.go.cr"),
    ("Alberto Campos", materias_dict["Música"], "alberto.campos.barrantes@mep.go.cr"),
    ("Rebeca Trejos", materias_dict["Emprendimiento"], "rebeca.trejos.cerdas@mep.go.cr"),
    ("William Mora", materias_dict["AySaC"], "william.mora.cantillo@mep.go.cr"),
    ("Lizeth Ortega", materias_dict["Inglés Tec."], "lizeth.ortega.rodriguez@mep.go.cr"),
    ("Natalia Castillo", materias_dict["Inglés Acad."], "natalia.castillo.ceballos@mep.go.cr"),
    ("Kenneth Castillo", materias_dict["Emprendimiento"], "kenneth.castillo.tenorio@mep.go.cr"),
    ("Magaly Pérez", materias_dict["Educación Física"], "magali.perez.fallas@mep.go.cr"),
    ("Josefa Espinoza", materias_dict["Ética"], "josefa.espinoza.rivera@mep.go.cr")
]

# Insertar profesores en la tabla
cursor.executemany('INSERT INTO profesores (nombre, materia_id, email) VALUES (?, ?, ?)', profesores)


# Guardar los cambios
conn.commit()

# Cerrar la conexión
conn.close()

print("Base de datos y tablas creadas exitosamente.")
print("Profesores, materias y archivos insertados correctamente.")
print("Triggers creados para actualizar automáticamente el conteo de recursos.")