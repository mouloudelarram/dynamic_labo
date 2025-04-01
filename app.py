# app.py
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
import csv
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'votre_clef_secrete'  # Nécessaire pour les messages flash

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}
CSV_FILE = 'data/equipments.csv'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Création des dossiers nécessaires s'ils n'existent pas
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data', exist_ok=True)

# Initialiser le fichier CSV s'il n'existe pas
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['id', 'designation', 'description', 'classification', 'matiere', 'image', 'pdfs'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def read_equipments():
    equipments = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                equipments.append(row)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier CSV: {e}")
    return equipments

def write_equipments(equipments):
    try:
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
            fieldnames = ['id', 'designation', 'description', 'classification', 'matiere', 'image', 'pdfs']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for equipment in equipments:
                writer.writerow(equipment)
        return True
    except Exception as e:
        print(f"Erreur lors de l'écriture dans le fichier CSV: {e}")
        return False

def get_equipment_by_id(equipment_id):
    equipments = read_equipments()
    for equipment in equipments:
        if equipment['id'] == equipment_id:
            return equipment
    return None

@app.route('/')
def index():
    equipments = read_equipments()
    return render_template('index.html', equipments=equipments)

@app.route('/equipment/<equipment_id>')
def equipment_details(equipment_id):
    equipment = get_equipment_by_id(equipment_id)
    if equipment:
        return render_template('equipment_details.html', equipment=equipment)
    flash('Équipement non trouvé', 'error')
    return redirect(url_for('index'))

@app.route('/equipment/<equipment_id>/<option>')
def equipment_option(equipment_id, option):
    equipment = get_equipment_by_id(equipment_id)
    if equipment and option in ['utilisation', 'maintenance']:
        return render_template('equipment_option.html', equipment=equipment, option=option)
    flash('Option ou équipement non trouvé', 'error')
    return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
def add_equipment():
    if request.method == 'POST':
        designation = request.form.get('designation', '')
        description = request.form.get('description', '')
        classification = request.form.get('classification', '')
        matiere = request.form.get('matiere', '')
        
        # Gestion de l'image
        image_filename = ''
        if 'image' in request.files:
            image = request.files['image']
            if image and allowed_file(image.filename):
                image_filename = secure_filename(f"{uuid.uuid4()}_{image.filename}")
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
        
        # Gestion des PDFs
        pdf_filenames = []
        if 'pdfs' in request.files:
            pdfs = request.files.getlist('pdfs')
            for pdf in pdfs:
                if pdf and allowed_file(pdf.filename):
                    pdf_filename = secure_filename(f"{uuid.uuid4()}_{pdf.filename}")
                    pdf.save(os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename))
                    pdf_filenames.append(pdf_filename)
        
        # Création du nouvel équipement
        new_equipment = {
            'id': str(uuid.uuid4()),
            'designation': designation,
            'description': description,
            'classification': classification,
            'matiere': matiere,
            'image': image_filename,
            'pdfs': ';'.join(pdf_filenames)  # Stocker les noms de fichiers PDF séparés par des points-virgules
        }
        
        # Ajout à la liste des équipements
        equipments = read_equipments()
        equipments.append(new_equipment)
        
        if write_equipments(equipments):
            flash('Équipement ajouté avec succès', 'success')
            return redirect(url_for('index'))
        else:
            flash('Erreur lors de l\'ajout de l\'équipement', 'error')
    
    return render_template('add_equipment.html')

@app.route('/edit/<equipment_id>', methods=['GET', 'POST'])
def edit_equipment(equipment_id):
    equipments = read_equipments()
    equipment = get_equipment_by_id(equipment_id)
    
    if not equipment:
        flash('Équipement non trouvé', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Mise à jour des informations de base
        equipment['designation'] = request.form.get('designation', '')
        equipment['description'] = request.form.get('description', '')
        equipment['classification'] = request.form.get('classification', '')
        equipment['matiere'] = request.form.get('matiere', '')
        
        # Mise à jour de l'image si une nouvelle est fournie
        if 'image' in request.files and request.files['image'].filename:
            image = request.files['image']
            if allowed_file(image.filename):
                # Suppression de l'ancienne image si elle existe
                if equipment['image'] and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], equipment['image'])):
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], equipment['image']))
                
                image_filename = secure_filename(f"{uuid.uuid4()}_{image.filename}")
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
                equipment['image'] = image_filename
        
        # Ajout de nouveaux PDFs si fournis
        if 'pdfs' in request.files:
            pdfs = request.files.getlist('pdfs')
            current_pdfs = equipment['pdfs'].split(';') if equipment['pdfs'] else []
            
            for pdf in pdfs:
                if pdf and pdf.filename and allowed_file(pdf.filename):
                    pdf_filename = secure_filename(f"{uuid.uuid4()}_{pdf.filename}")
                    pdf.save(os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename))
                    current_pdfs.append(pdf_filename)
            
            equipment['pdfs'] = ';'.join(filter(None, current_pdfs))
        
        # Mise à jour dans la liste
        for i, eq in enumerate(equipments):
            if eq['id'] == equipment_id:
                equipments[i] = equipment
                break
        
        if write_equipments(equipments):
            flash('Équipement mis à jour avec succès', 'success')
            return redirect(url_for('equipment_details', equipment_id=equipment_id))
        else:
            flash('Erreur lors de la mise à jour de l\'équipement', 'error')
    
    return render_template('edit_equipment.html', equipment=equipment)

@app.route('/delete/<equipment_id>', methods=['POST'])
def delete_equipment(equipment_id):
    equipments = read_equipments()
    equipment = get_equipment_by_id(equipment_id)
    
    if not equipment:
        flash('Équipement non trouvé', 'error')
        return redirect(url_for('index'))
    
    # Suppression des fichiers associés
    if equipment['image'] and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], equipment['image'])):
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], equipment['image']))
    
    if equipment['pdfs']:
        for pdf in equipment['pdfs'].split(';'):
            if pdf and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], pdf)):
                os.remove(os.path.join(app.config['UPLOAD_FOLDER'], pdf))
    
    # Suppression de l'équipement de la liste
    equipments = [eq for eq in equipments if eq['id'] != equipment_id]
    
    if write_equipments(equipments):
        flash('Équipement supprimé avec succès', 'success')
    else:
        flash('Erreur lors de la suppression de l\'équipement', 'error')
    
    return redirect(url_for('index'))

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)