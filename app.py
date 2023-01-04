from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
import psycopg2
from model import *
from dotenv import load_dotenv
import os
import bcrypt
import json
import pandas as pd
from connexion_direct import update_or_insert_2



app = Flask(__name__)

load_dotenv()
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql+psycopg2://" + os.getenv("UTILISATEUR")+":"+os.getenv("MDP")+"@"+os.getenv("SERVEUR")
db = SQLAlchemy(app)

# Schema BDD
class Produits(db.Model):
    __tablename__ = 'produits'
    id_magasin = db.Column(db.Integer,primary_key=True)
    id_article = db.Column(db.BigInteger,primary_key=True)
    carbone = db.Column(db.String())
    name = db.Column(db.String())

    def __init__(self, id_magasin,id_article, carbone,name):
        self.id_magasin=id_magasin
        self.id_article=id_article
        self.carbone = carbone
        self.name=name
        
        
class ProduitsManquants(db.Model):
    __tablename__ = 'produitsManquants'
    id_magasin = db.Column(db.Integer,primary_key=True)
    id_article = db.Column(db.BigInteger,primary_key=True)
    name = db.Column(db.String())

    def __init__(self, id_magasin,id_article,name):
        self.id_magasin=id_magasin
        self.id_article=id_article
        self.name=name

class Utilisateur(db.Model):
    __tablename__ = 'utilisateur'
    id_magasin = db.Column(db.Integer, primary_key=True)
    password = db.Column(db.Text)

    def __init__(self, id_user,password):
        self.id_magasin=id_user
        self.password=password


@app.route('/')
def hello():
    return "Bienvenue sur l'API de Tickarbone: https://www.tickarbone.fr/"

"""
@app.route('/temp')
def temp():
    return {"hello": "temp"}


@app.route('/insert')
def insert():
    prod = Produits(1,2, '128')
    db.session.add(prod)
    db.session.commit()
    return "done"

@app.route('/drop_all')
def drop():
    db.drop_all()
    return "done"


@app.route('/select/all') 
def select():
    qry=Produits.query.all()
    return {'data': [
         {'id_produit':record.id_article, 'id_magasin':
            record.id_magasin, 'name' :record.name,'carbone' :record.carbone}
        for record in qry
       ]}


@app.route('/select/sans_protection',methods=['GET'])
def select_2():
    id_magasin=request.args.get('id_magasin')
    id_article=request.args.get('id_article')
    qry=Produits.query.filter_by(id_magasin=id_magasin).filter_by(id_article=id_article)
    return {'data': [
         {'id_article':record.id_article, 'id_magasin':
            record.id_magasin, 'name' :record.name,'carbone' :record.carbone}
        for record in qry
       ]}
"""
#selectionne un produit
@app.route('/select/avec_protection',methods=['GET'])
def select_3():
    mdp=request.args.get('password')
    id_magasin=request.args.get('id_magasin')
    id_article=request.args.get('id_article')
    res = password(id_magasin,mdp)
    if res ==True:
        qry=Produits.query.filter_by(id_magasin=id_magasin).filter_by(id_article=id_article)
        print(qry)
        return {'data': [
         {'id_article':record.id_article, 'id_magasin':
            record.id_magasin, 'name' :record.name,'carbone' :record.carbone}
        for record in qry
       ]}
    else:
        return {"statut":"nom d'utilisateur ou mot de passe incorrect."}

# selectionner toute la base d'un magasin
@app.route('/select/magasin',methods=['GET'])
def select_4():
    mdp=request.args.get('password')
    id_magasin=request.args.get('id_magasin')
    res = password(id_magasin,mdp)
    if res ==True:
        qry=Produits.query.filter_by(id_magasin=id_magasin)
        print(qry)
        return {'data': [
         {'id_article':record.id_article, 'id_magasin':
            record.id_magasin, 'name' :record.name,'carbone' :record.carbone}
        for record in qry
       ]}
    else:
        return {"statut":"nom d'utilisateur ou mot de passe incorrect."}


# recevoir un json et l'afficher
@app.route('/envoi_json',methods=['POST'])
def process_json():
    content_type = request.headers.get('Content-Type')
    id_magasin = request.headers.get('id_magasin')
    mdp= request.headers.get('password')   
    res = password(id_magasin,mdp)
    if res== True:
        if (content_type == 'application/json'):
            json_data = request.json

            # recupere la liste des produits du magasin (id_article + carbone)
            qry2 = db.engine.execute(f"select id_article,carbone from produits where id_magasin = {id_magasin}")
            qry_temp=list(qry2) # cree une copie car qry2 est un curseur
            
            qry3 = dict((x[0],x[1]) for x in list(qry_temp)) # cree un dictionnaire clé: id_article, valeur: carbone
            qry4=list(map(lambda x: (str(x[0])),list(qry_temp))) # cree une liste des id_articles

            new_json=[] # liste contenant la liste des produits à renvoyer
            for i in json_data['data']:
                if str(i["id_article"]) in qry4:
                    new_json.append({"id_article":i["id_article"],'carbone':qry3[i["id_article"]]})
                else:
                    #ajouter à la base des produits manquants
                    produitsManquants =  ProduitsManquants(id_magasin, i["id_article"],i["name"])
                    db.session.add(produitsManquants)
                    #prod_manquants.append({"id_magasin":id_magasin,"id_article":i["id_article"],"name":i["name"]})
            db.session.commit()
            return {"data":new_json}
        else:
            return 'Content-Type not supported!'
    else:
        return {"statut":"nom d'utilisateur ou mot de passe incorrect."}
    
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/excelupload',methods=['POST'])
def upload_file():
    file = request.files['file']
    update_or_insert_2(file,"(kgCO2/kgproduit)","Libellé","ID magasin","ID article")
    #colonne_carbone,colonne_name,colonne_id_magasin,colonne_id_produit
    """
    qry=Produits.query.filter_by(id_magasin="6").all()
    return {'data': [
     {'id_article':record.id_article, 'id_magasin':
        record.id_magasin, 'name' :record.name,'carbone' :record.carbone}
    for record in qry
   ]}
    """
    return render_template('index.html')

    '''
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            UPLOAD_FOLDER = './upload_dir/'
            CreateNewDir()
            global UPLOAD_FOLDER
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
            '''



# Format envoi_json: curl -X POST -H "Content-type: application/json" -H "password: jaimelebio" -H "id_magasin: 1" -d "" "localhost:8080/envoi_json"
"""
@app.route('/test',methods=['POST'])
def test():
    json = request.data
    print(json)
    return str(json)
    #query=Produits.query.filter(Produits.id_article.in_(my_list)).all()
    #return str(query)
""" 


# Fonctions support
def password(id_magasin,password):
    mdp_encoded=password.encode('utf-8')
    qry = Utilisateur.query.where(Utilisateur.id_magasin==id_magasin).first()
    hashed=qry.password
    hashed=hashed.encode('utf-8')
    result = bcrypt.checkpw(mdp_encoded, hashed)
    return result
    

if __name__ == '__main__':
    app.run(port=8080,debug=True)