from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error
import io
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import os
import re

from dotenv import load_dotenv

# Configuración inicial de Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Cargar variables de entorno
load_dotenv()

# Configuración de Google Drive
GOOGLE_CREDENTIALS_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_ID = "1Q4M8tpF2MkOvjjBQBWUJiEzh2kXJ7w47"
UPLOAD_FOLDER = 'static/uploads'

@app.before_request
def logger():
    iniciar_subproceso()
    print(f"Request Method: {request.method} | Request URL: {request.url}")

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT'),
            database=os.getenv('DB_NAME')
        )
        if conn.is_connected():
            print("Conexión exitosa a la base de datos")
            return conn
    except Error as e:
        print(f"Error al conectar a MySQL: {e}")
        return None



def text_to_pdf(text, filename):
    filepath = os.path.join('static/uploads', filename)
    pdf = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles with Unicode support
    custom_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        spaceAfter=30,
        encoding='utf-8'
    )
    
    custom_heading2 = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Normal'],
        fontSize=18,
        spaceAfter=20,
        encoding='utf-8'
    )
    
    custom_normal = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        encoding='utf-8'
    )
    
    # Create bullet style
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        leftIndent=20,
        encoding='utf-8'
    )
    
    story = []
    
    # Process text line by line with error handling
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        try:
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # Process tables
            if line.startswith('|'):
                table_data = []
                table_lines = []
                
                while i < len(lines) and lines[i].strip().startswith('|'):
                    table_lines.append(lines[i].strip())
                    i += 1
                
                headers = [cell.strip() for cell in table_lines[0].split('|')[1:-1]]
                rows = [[cell.strip() for cell in row.split('|')[1:-1]] 
                       for row in table_lines[2:]]
                
                table_data = [headers] + rows
                table = Table(table_data)
                
                table_style = TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                    ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 10),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('PADDING', (0, 0), (-1, -1), 6),
                ])
                table.setStyle(table_style)
                story.append(table)
                story.append(Spacer(1, 12))
                continue
            
            # Process titles and formatting
            if line.startswith('# '):
                story.append(Paragraph(line[2:].strip(), custom_title))
            elif line.startswith('## '):
                story.append(Paragraph(line[3:].strip(), custom_heading2))
            elif line.startswith('*') and line.endswith('*'):
                content = line[1:-1].strip()
                story.append(Paragraph(f"<para><b>{content}</b></para>", custom_normal))
            elif line.startswith('_') and line.endswith('_'):
                content = line[1:-1].strip()
                story.append(Paragraph(f"<para><i>{content}</i></para>", custom_normal))
            elif line.startswith('<u>') and line.endswith('</u>'):
                content = line[3:-4].strip()
                story.append(Paragraph(f"<para><u>{content}</u></para>", custom_normal))
            # Handle bullet points differently
            elif line.startswith('- '):
                content = line[2:].strip()
                story.append(Paragraph(
                    f"• {content}",
                    bullet_style
                ))
            # Handle numbered lists differently
            elif re.match(r'^\d+\.\s', line):
                number, content = line.split('. ', 1)
                story.append(Paragraph(
                    f"{number}. {content}",
                    bullet_style
                ))
            # Handle colored text
            elif '{' in line and '}' in line:
                try:
                    color_match = re.search(r'\{([^}]+)\}([^{]+)\{/color\}', line)
                    if color_match:
                        color = color_match.group(1)
                        content = color_match.group(2)
                        story.append(Paragraph(
                            f"<para><font color='{color}'>{content}</font></para>",
                            custom_normal
                        ))
                except:
                    story.append(Paragraph(line, custom_normal))
            else:
                story.append(Paragraph(line, custom_normal))
            
            story.append(Spacer(1, 12))
            i += 1
            
        except Exception as e:
            print(f"Error processing line {i}: {str(e)}")
            # Skip problematic line and continue with the next
            i += 1
            continue
    
    try:
        pdf.build(story)
        return filepath
    except Exception as e:
        print(f"Error building PDF: {str(e)}")
        return None
@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get current datetime for comparison
    now = datetime.now()

    # Obtener tareas
    query_tareas = '''
    SELECT 
        tareas.id,
        tareas.titulo,
        tareas.descripcion,
        tareas.fecha_vencimiento,
        tareas.fecha_creacion,
        profesores.nombre AS profesor_nombre,
        materias.nombre AS materia_nombre,
        materias.icono AS materia_icono
    FROM tareas
    JOIN profesores ON tareas.profesor_id = profesores.id
    JOIN materias ON tareas.materia_id = materias.id
    ORDER BY tareas.fecha_creacion DESC
    LIMIT 3
    '''
    cursor.execute(query_tareas)
    tareas_raw = cursor.fetchall()
    
    # Convert the raw tuples to dictionaries and process dates
    tareas = []
    for tarea in tareas_raw:
        # Convert the date string to datetime object
        fecha_vencimiento = datetime.strptime(str(tarea[3]), '%Y-%m-%d %H:%M:%S') if tarea[3] else None
        fecha_creacion = datetime.strptime(str(tarea[4]), '%Y-%m-%d %H:%M:%S') if tarea[4] else None
        
        tarea_dict = {
            'id': tarea[0],
            'titulo': tarea[1],
            'descripcion': tarea[2],
            'fecha_vencimiento': fecha_vencimiento,
            'fecha_creacion': fecha_creacion,
            'profesor_nombre': tarea[5],
            'materia_nombre': tarea[6],
            'materia_icono': tarea[7]
        }
        tareas.append(tarea_dict)

    # Obtener archivos
    query_archivos = '''
    SELECT 
        files.id,
        files.title,
        files.date,
        files.filename,
        files.autor,
        files.extension,
        profesores.nombre as profesor,
        materias.nombre AS materia_nombre,
        materias.icono AS materia_icono
    FROM files
    JOIN materias ON files.materia_id = materias.id
    JOIN profesores ON files.profesor_id = profesores.id
    ORDER BY files.date DESC
    LIMIT 3
    '''
    cursor.execute(query_archivos)
    archivos = cursor.fetchall()
    
    archivos_formateados = []
    for archivo in archivos:
        archivo_dict = {
            'id': archivo[0],
            'title': archivo[1],
            'date': archivo[2].strftime('%Y-%m-%d %H:%M:%S'),
            'filename': archivo[3],
            'autor': archivo[4],
            'extension': archivo[5],
            'profesor': archivo[6],
            'materia_nombre': archivo[7],
            'materia_icono': archivo[8]
        }
        archivos_formateados.append(archivo_dict)

    conn.close()
    return render_template('index.html', 
                         tareas=tareas,
                         archivos=archivos_formateados,
                         now=datetime.now())

@app.route('/condiciones')
def condiciones():
    return render_template('terminos.html')

@app.route('/data/<tipo>')
def data(tipo):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if tipo == "profesores":
            query = '''
            SELECT 
                profesores.id, 
                profesores.nombre, 
                profesores.email, 
                profesores.materia_id,
                materias.nombre AS materia_nombre, 
                materias.icono AS materia_icono
            FROM profesores
            JOIN materias ON profesores.materia_id = materias.id
            '''
            cursor.execute(query)
            data = [{
                'id': row[0],
                'nombre': row[1],
                'email': row[2],
                'materia_id': row[3],
                'materia_nombre': row[4],
                'materia_icono': row[5]
            } for row in cursor.fetchall()]

        elif tipo == "materias":
            query = '''
            SELECT 
                materias.id,
                materias.nombre,
                materias.icono,
                materias.recursos,
                COUNT(profesores.id) AS profesores
            FROM materias
            LEFT JOIN profesores ON materias.id = profesores.materia_id
            GROUP BY materias.id
            '''
            cursor.execute(query)
            data = [{
                'id': row[0],
                'nombre': row[1],
                'icono': row[2],
                'recursos': row[3],
                'profesores': row[4]
            } for row in cursor.fetchall()]

        elif tipo == "tareas":
            query = '''
            SELECT 
                tareas.id,
                tareas.titulo,
                tareas.descripcion,
                tareas.fecha_vencimiento,
                tareas.fecha_creacion,
                profesores.id AS profesor_id,
                profesores.nombre AS profesor_nombre,
                profesores.email AS profesor_email,
                materias.id AS materia_id,
                materias.nombre AS materia_nombre,
                materias.icono AS materia_icono
            FROM tareas
            JOIN profesores ON tareas.profesor_id = profesores.id
            JOIN materias ON tareas.materia_id = materias.id
            ORDER BY tareas.fecha_vencimiento
            '''
            cursor.execute(query)
            data = [{
                'id': row[0],
                'titulo': row[1],
                'descripcion': row[2],
                'fecha_vencimiento': row[3].strftime('%Y-%m-%d'),
                'fecha_creacion': row[4].strftime('%Y-%m-%d %H:%M:%S'),
                'profesor_id': row[5],
                'profesor_nombre': row[6],
                'profesor_email': row[7],
                'materia_id': row[8],
                'materia_nombre': row[9],
                'materia_icono': row[10]
            } for row in cursor.fetchall()]

        elif tipo == "recursos":
            query = '''
            SELECT 
                files.id, 
                files.title, 
                files.date, 
                files.filename, 
                files.autor,
                files.extension,
                materias.nombre AS materia_nombre, 
                materias.icono AS materia_icono 
            FROM files 
            JOIN materias ON files.materia_id = materias.id 
            ORDER BY files.date DESC
            '''
            cursor.execute(query)
            data = [{
                'id': row[0],
                'title': row[1],
                'date': row[2].strftime('%Y-%m-%d %H:%M:%S'),
                'filename': row[3],
                'autor': row[4],
                'extension': row[5],
                'materia_nombre': row[6],
                'materia_icono': row[7]
            } for row in cursor.fetchall()]

        else:
            data = []
        
        return render_template('api.html', data=data, tipo=tipo)
    
    finally:
        conn.close()

@app.route('/tareas')
def tareas():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Obtener profesores
        cursor.execute('''
            SELECT 
                profesores.id, 
                profesores.nombre, 
                profesores.materia_id,
                materias.nombre AS materia_nombre
            FROM profesores
            JOIN materias ON profesores.materia_id = materias.id
            ORDER BY profesores.nombre
        ''')
        profesores = [{
            'id': row[0],
            'nombre': row[1],
            'materia_id': row[2],
            'materia_nombre': row[3]
        } for row in cursor.fetchall()]

        # Obtener materias
        cursor.execute('SELECT id, nombre, icono FROM materias ORDER BY nombre')
        materias = [{
            'id': row[0],
            'nombre': row[1],
            'icono': row[2]
        } for row in cursor.fetchall()]

        # Obtener tareas
        cursor.execute('''
            SELECT 
                tareas.id,
                tareas.titulo,
                tareas.descripcion,
                tareas.fecha_vencimiento,
                profesores.nombre AS profesor_nombre,
                materias.nombre AS materia_nombre,
                materias.icono AS materia_icono
            FROM tareas
            JOIN profesores ON tareas.profesor_id = profesores.id
            JOIN materias ON tareas.materia_id = materias.id
            ORDER BY tareas.fecha_vencimiento
        ''')
        tareas = [{
            'id': row[0],
            'titulo': row[1],
            'descripcion': row[2],
            'fecha_vencimiento': row[3].strftime('%Y-%m-%d'),
            'profesor_nombre': row[4],
            'materia_nombre': row[5],
            'materia_icono': row[6]
        } for row in cursor.fetchall()]

        return render_template('tareas.html', 
                             profesores=profesores,
                             materias=materias,
                             tareas=tareas)
    
    finally:
        conn.close()

@app.route('/add_tarea', methods=['POST'])
def add_tarea():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO tareas (titulo, descripcion, fecha_vencimiento, profesor_id, materia_id)
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            request.form['titulo'],
            request.form['descripcion'],
            request.form['fecha_vencimiento'],
            request.form['profesor_id'],
            request.form['materia_id']
        ))
        conn.commit()
        return redirect(url_for('data', tipo="tareas"))
    
    finally:
        conn.close()

@app.route('/edit_tarea/<int:id>', methods=['GET', 'POST'])
def edit_tarea(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if request.method == 'POST':
            cursor.execute('''
                UPDATE tareas
                SET titulo = %s,
                    descripcion = %s,
                    fecha_vencimiento = %s,
                    profesor_id = %s,
                    materia_id = %s
                WHERE id = %s
            ''', (
                request.form['titulo'],
                request.form['descripcion'],
                request.form['fecha_vencimiento'],
                request.form['profesor_id'],
                request.form['materia_id'],
                id
            ))
            conn.commit()
            return redirect(url_for('tareas'))

        # Obtener datos para el formulario
        cursor.execute('SELECT * FROM tareas WHERE id = %s', (id,))
        tarea = cursor.fetchone()
        tarea_dict = {
            'id': tarea[0],
            'titulo': tarea[1],
            'descripcion': tarea[2],
            'fecha_vencimiento': tarea[3].strftime('%Y-%m-%d'),
            'profesor_id': tarea[4],
            'materia_id': tarea[5]
        }

        cursor.execute('''
            SELECT 
                profesores.id, 
                profesores.nombre, 
                profesores.materia_id,
                materias.nombre AS materia_nombre
            FROM profesores
            JOIN materias ON profesores.materia_id = materias.id
            ORDER BY profesores.nombre
        ''')
        profesores = [{
            'id': row[0],
            'nombre': row[1],
            'materia_id': row[2],
            'materia_nombre': row[3]
        } for row in cursor.fetchall()]

        cursor.execute('SELECT id, nombre, icono FROM materias ORDER BY nombre')
        materias = [{
            'id': row[0],
            'nombre': row[1],
            'icono': row[2]
        } for row in cursor.fetchall()]

        return render_template('edit_tarea.html', 
                             tarea=tarea_dict,
                             profesores=profesores,
                             materias=materias)
    
    finally:
        conn.close()

@app.route('/delete_tarea/<int:id>')
def delete_tarea(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM tareas WHERE id = %s', (id,))
        conn.commit()
        return redirect(url_for('tareas'))
    
    finally:
        conn.close()

def get_drive_service():
    creds = Credentials.from_service_account_file(GOOGLE_CREDENTIALS_FILE, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)

def upload_to_drive(file, filename=None, content_type=None):
    """
    Sube un archivo a Google Drive
    
    Args:
        file: Puede ser FileStorage o BufferedReader
        filename: Nombre del archivo (opcional, requerido si file es BufferedReader)
        content_type: Tipo de contenido (opcional, requerido si file es BufferedReader)
    """
    drive_service = get_drive_service()
    
    # Si es un archivo abierto (BufferedReader), usar los parámetros proporcionados
    if isinstance(file, io.BufferedReader):
        file_metadata = {"name": filename, "parents": [FOLDER_ID]}
        media = MediaIoBaseUpload(file, mimetype=content_type or 'application/octet-stream', resumable=True)
    else:
        # Si es FileStorage, usar sus atributos
        file_metadata = {"name": file.filename, "parents": [FOLDER_ID]}
        media = MediaIoBaseUpload(file, mimetype=file.content_type, resumable=True)
    
    file_drive = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return f"https://drive.google.com/uc?id={file_drive.get('id')}"

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        print(request.form)
        titulo = request.form['title']
        autor = request.form['autor']
        materia = request.form['subject']
        profesor = request.form['profesor']
        text = request.form['text']
        file = request.files.get('file')
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        try:
            cursor.execute('SELECT id FROM materias WHERE nombre = %s', (materia,))
            if not (materia := cursor.fetchone()):
                return "Materia no encontrada", 404
            # Procesar archivo o texto
            if file:
                # Si es un archivo, guardarlo localmente primero
                filename = secure_filename(file.filename)
                local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(local_path)
                
                # Luego subirlo a Drive
                with open(local_path, 'rb') as f:
                    file_url = upload_to_drive(f, filename)
                
                extension = filename.split('.')[-1].lower()
            elif text:
                # Si es texto, convertirlo a PDF y guardarlo localmente
                filename = secure_filename(f"{titulo}.pdf")
                local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                text_to_pdf(text, local_path)
                
                # Luego subirlo a Drive
                with open(local_path, 'rb') as f:
                    file_url = upload_to_drive(f)
                
                extension = 'pdf'
            else:
                return "No se proporcionó contenido", 400
            cursor.execute('''
                INSERT INTO files (title, materia_id, date, filename, file_url, autor, profesor_id, extension)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                titulo,
                materia[0],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                filename,
                file_url,
                autor,
                profesor,
                extension
            ))
            conn.commit()
            return redirect(url_for('index'))
        finally:
            conn.close()

    # GET request
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT id, nombre FROM materias')
        materias = [{"id": row[0], "nombre": row[1]} for row in cursor.fetchall()]
        cursor.execute('SELECT id, nombre FROM profesores')
        profesores = [{"id": row[0], "nombre": row[1]} for row in cursor.fetchall()]
        return render_template('upload.html', materias=materias, profesores=profesores)
    
    finally:
        conn.close()

@app.route('/search')
def search():
    return render_template('search.html')

@app.route('/recursos/<tipo>')
def recursos(tipo):
    valor = request.args.get('valor')
    if not valor:
        return "Parámetro 'valor' requerido", 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if tipo == 'materia':
            cursor.execute('''
                SELECT 
                    files.id,
                    files.title,
                    files.date,
                    files.filename,
                    files.autor,
                    files.extension,
                    materias.nombre AS materia_nombre,
                    materias.icono AS materia_icono
                FROM files
                JOIN materias ON files.materia_id = materias.id
                WHERE materias.nombre = %s
                ORDER BY files.date DESC
            ''', (valor,))
        
        elif tipo == 'profesor':
            cursor.execute('''
                SELECT 
                    files.id,
                    files.title,
                    files.date,
                    files.filename,
                    files.autor,
                    files.extension,
                    profesores.nombre AS profesor_nombre,
                    materias.nombre AS materia_nombre,
                    materias.icono AS materia_icono
                FROM files
                JOIN materias ON files.materia_id = materias.id
                JOIN profesores ON files.profesor_id = profesores.id
                WHERE profesores.nombre = %s
                ORDER BY files.date DESC
            ''', (valor,))
        
        elif tipo == 'clave':
            cursor.execute('''
                SELECT 
                    files.id,
                    files.title,
                    files.date,
                    files.filename,
                    files.autor,
                    files.extension,
                    profesores.nombre AS profesor_nombre,
                    materias.nombre AS materia_nombre,
                    materias.icono AS materia_icono
                FROM files
                JOIN materias ON files.materia_id = materias.id
                JOIN profesores ON files.profesor_id = profesores.id
                WHERE files.title LIKE %s
                ORDER BY files.date DESC
            ''', (f'%{valor}%',))
        
        else:
            return "Tipo no válido", 400

        recursos = [{
            'id': row[0],
            'title': row[1],
            'date': row[2].strftime('%Y-%m-%d %H:%M:%S'),
            'filename': row[3],
            'autor': row[4],
            'extension': row[5],
            'materia_nombre': row[6] if tipo == 'materia' else row[7],
            'materia_icono': row[7] if tipo == 'materia' else row[8],
            'profesor_nombre': row[6] if tipo != 'materia' else None
        } for row in cursor.fetchall()]

        return render_template('recursos.html', 
                             recursos=recursos,
                             tipo=tipo,
                             valor=valor)
    
    finally:
        conn.close()

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER,filename)


import threading
import time
import requests
def peticion_periodica():
    while True:
        # Llamar a la función que deseas ejecutar
        requests.get("https://zenithhub.onrender.com")
        time.sleep(30)

bot = False
# Iniciar el subproceso
def iniciar_subproceso():
    global bot
    if not bot:
        bot = True
        t = threading.Thread(target=peticion_periodica)
        t.daemon = True  # Asegura que el hilo termine cuando el programa termine
        t.start()




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090, debug=True)