import os
from flask import Blueprint, abort, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user
import ldap3
from sqlalchemy import text

from backend.shared.environment import required_env

from app.utils.db_utils import get_engine
from app.utils.permissions import get_permission

jdt_extra_bp = Blueprint('jdt_extra', __name__)

# Caminho para as fotos (ajuste conforme necessário)
PHOTOS_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'app', 'static', 'extra')

@jdt_extra_bp.before_request
def route_auth():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login', next=request.url))
    
    if not get_permission('GENERAL').can():
        return abort(403)


def extra_login_method(user):
    base = 'ou=EmpresasRandon,dc=randon,dc=com,dc=br'
    ld = ldap3.Server('SVH-DC-21.randon.com.br', use_ssl=False)
    ld_conn = ldap3.Connection(ld, user=required_env("DJ_LDAP_USER"), password=required_env("DJ_LDAP_PASSWORD"),
                              authentication=ldap3.NTLM)
    ld_conn.bind()
    ld_conn.search(base, f'(&(objectCategory=Person)(description=*{user}))',
                  attributes=ldap3.ALL_ATTRIBUTES)

    if ld_conn.entries:
        return "AUTHORIZED;" + str(ld_conn.entries[0].displayName)

    return 'denied'


@jdt_extra_bp.route('/extra', methods=['GET'])
def extra_main():
    # Se for fabrica_jost e já tem sessão, usar informações da sessão
    if current_user.id == 'fabrica_jost':
        if 'user_id' in session:
            return render_template('jdt.temp/main.html', 
                                  user=session['user_id'], 
                                  user_name=session.get('user_name', 'Usuário'),
                                  is_session_active=True)
        # Se não tem sessão, mostrar tela de login
        return render_template('jdt.temp/main.html', 
                              user=current_user.id,
                              is_session_active=False)
    
    # Se não for fabrica_jost, criar/atualizar a sessão automaticamente
    else:
        # Criar sessão para usuário normal
        session['user_id'] = current_user.id
        session['user_name'] = current_user.name if hasattr(current_user, 'name') else current_user.id
        
        return render_template('jdt.temp/main.html', 
                              user=current_user.id,
                              user_name=session['user_name'],
                              is_session_active=True)
    
@jdt_extra_bp.route('/extra', methods=['POST'])
def extra_main_post():
    """Rota POST para manter a sessão ativa quando o botão Voltar é pressionado"""
    # Verificar se há um user_id no formulário
    form_user_id = request.form.get('user_id')
    
    # Se há um ID de usuário no formulário e não há sessão atual, usá-lo para criar sessão
    if form_user_id and 'user_id' not in session:
        session['user_id'] = form_user_id
        
        # Se for o usuário fabrica_jost, tente buscar o nome pela função de login
        if current_user.id == 'fabrica_jost':
            try:
                auth_response = extra_login_method(form_user_id)
                if auth_response != 'denied':
                    session['user_name'] = auth_response.split(';')[1]
            except:
                # Em caso de erro, usar um nome genérico
                session['user_name'] = 'Usuário'
    
    # Renderizar a página principal com as informações da sessão
    return render_template('jdt.temp/main.html', 
                         user=session.get('user_id', current_user.id),
                         user_name=session.get('user_name', 'Usuário'),
                         is_session_active=True if 'user_id' in session else False)


@jdt_extra_bp.route('/extra/login', methods=['POST'])
def extra_login():
    # Permitir login apenas para fabrica_jost ou admin
    if current_user.id != 'fabrica_jost' and not current_user.admin:
        return abort(403)
    
    if request.is_json:
        user = request.get_json()['user']
        
        auth_response = extra_login_method(user)
        if auth_response == 'denied':
            abort(403)
        
        # Armazenar ID do usuário na sessão
        session['user_id'] = user
        session['user_name'] = auth_response.split(';')[1]
        
        return auth_response
    else:
        abort(403)


@jdt_extra_bp.route('/extra/logout', methods=['GET'])
def extra_logout():
    # Limpar a sessão
    session.pop('user_id', None)
    session.pop('user_name', None)
    
    # Redirecionar para a página principal
    return redirect(url_for('jdt_extra.extra_main'))


@jdt_extra_bp.route('/extra/votar/<categoria>', methods=['GET'])
def votar_categoria_get(categoria):

    return redirect(url_for('jdt_extra.extra_main'))

@jdt_extra_bp.route('/extra/votar/<categoria>', methods=['POST'])
def votar_categoria_post(categoria):
    # Verificar se usuário está autenticado
    if 'user_id' not in session:
        # Se for fabrica_jost e não tem sessão, redirecionar para login
        if current_user.id == 'fabrica_jost':
            return redirect(url_for('jdt_extra.extra_main'))
        else:
            # Se for outro usuário, criar sessão automaticamente
            session['user_id'] = current_user.id
            session['user_name'] = current_user.name if hasattr(current_user, 'name') else current_user.id
    
    # Validar categoria
    categorias_validas = ['bagunceira', 'estilosa', 'braba', 'careta']
    if categoria not in categorias_validas:
        abort(400)
    
    user_id = session.get('user_id')
    user_name = session.get('user_name', 'Usuário')
    
    # Registrar acesso à categoria no banco de dados
    engine = get_engine('jdt')
    try:
        with engine.begin() as conn:
            # Registrar acesso à categoria
            query = """
                INSERT INTO JDT_EXTRA_KIDS_DAY_CATEGORY_ACCESS 
                (user_id, category, access_time) 
                VALUES (:user_id, :category, GETDATE())
            """
            conn.execute(text(query), {"user_id": user_id, "category": categoria})
    except Exception as e:
        print(f"Erro ao registrar acesso: {e}")
    
    # Renderizar página de votação
    return render_template('jdt.temp/extra.html', 
                          categoria=categoria, 
                          user_id=user_id, 
                          nome_usuario=user_name)


@jdt_extra_bp.route('/extra/fotos/<categoria>', methods=['GET'])
def obter_fotos_categoria(categoria):
    # Verificar se usuário está autenticado
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    # Validar categoria
    categorias_validas = ['bagunceira', 'estilosa', 'braba', 'careta']
    if categoria not in categorias_validas:
        return jsonify({"error": "Categoria inválida"}), 400
    
    user_id = session.get('user_id')
    
    # Buscar fotos da categoria
    photos = []
    
    try:
        # Percorrer diretórios de participantes
        for participant_id in os.listdir(PHOTOS_BASE_PATH):
            participant_dir = os.path.join(PHOTOS_BASE_PATH, participant_id)
            
            # Verificar se é um diretório
            if not os.path.isdir(participant_dir):
                continue
            
            # Procurar fotos da categoria específica
            for file in os.listdir(participant_dir):
                if categoria.lower() in file.lower() and (file.endswith('.jpg') or file.endswith('.jpeg') or file.endswith('.png')):
                    photo_id = f"{participant_id}_{file}"
                    photo_path = f"/static/extra/{participant_id}/{file}"
                    
                    # Obter contagem de curtidas do banco
                    likes = get_photo_likes(photo_id)
                    
                    photos.append({
                        "id": photo_id,
                        "participant_id": participant_id,
                        "filename": file,
                        "url": photo_path,
                        "likes": likes
                    })
    except Exception as e:
        print(f"Erro ao buscar fotos: {e}")
        return jsonify({"error": "Erro ao buscar fotos"}), 500
    
    # Obter fotos que o usuário já curtiu
    liked_photos = get_user_liked_photos(user_id, categoria)
    
    return jsonify({
        "photos": photos,
        "liked_photos": liked_photos
    })


@jdt_extra_bp.route('/extra/curtir', methods=['POST'])
def curtir_foto():
    # Verificar se usuário está autenticado
    if 'user_id' not in session:
        return jsonify({"error": "Não autorizado"}), 401
    
    if not request.is_json:
        return jsonify({"error": "Requisição inválida"}), 400
    
    data = request.get_json()
    user_id = data.get('user_id')
    photo_id = data.get('photo_id')
    categoria = data.get('categoria')
    
    if not all([user_id, photo_id, categoria]):
        return jsonify({"error": "Parâmetros insuficientes"}), 400
    
    # Verificar se o usuário já curtiu esta foto
    already_liked = is_photo_liked_by_user(user_id, photo_id)
    
    try:
        engine = get_engine('jdt')
        with engine.begin() as conn:
            if already_liked:
                # Remover curtida (descurtir)
                query = """
                    DELETE FROM JDT_EXTRA_KIDS_DAY_LIKES 
                    WHERE user_id = :user_id AND photo_id = :photo_id
                """
                conn.execute(text(query), {
                    "user_id": user_id,
                    "photo_id": photo_id
                })
                message = "Curtida removida com sucesso"
                action = "unliked"
            else:
                # Adicionar curtida
                query = """
                    INSERT INTO JDT_EXTRA_KIDS_DAY_LIKES 
                    (user_id, photo_id, category, like_time) 
                    VALUES (:user_id, :photo_id, :category, GETDATE())
                """
                conn.execute(text(query), {
                    "user_id": user_id,
                    "photo_id": photo_id,
                    "category": categoria
                })
                message = "Curtida registrada com sucesso"
                action = "liked"
        
        # Obter contagem atualizada de curtidas
        likes_count = get_photo_likes(photo_id)
        
        return jsonify({
            "success": True, 
            "message": message,
            "action": action,
            "likes_count": likes_count
        })
    except Exception as e:
        print(f"Erro ao processar curtida: {e}")
        return jsonify({"error": "Erro ao processar curtida"}), 500


# Funções auxiliares

def get_photo_likes(photo_id):
    """Obter o número de curtidas de uma foto"""
    try:
        engine = get_engine('jdt')
        with engine.connect() as conn:
            query = """
                SELECT COUNT(*) as likes 
                FROM JDT_EXTRA_KIDS_DAY_LIKES 
                WHERE photo_id = :photo_id
            """
            result = conn.execute(text(query), {"photo_id": photo_id}).fetchone()
            return result[0] if result else 0
    except Exception as e:
        print(f"Erro ao obter curtidas: {e}")
        return 0


def get_user_liked_photos(user_id, categoria):
    """Obter lista de fotos que o usuário já curtiu na categoria"""
    try:
        engine = get_engine('jdt')
        with engine.connect() as conn:
            query = """
                SELECT photo_id 
                FROM JDT_EXTRA_KIDS_DAY_LIKES 
                WHERE user_id = :user_id AND category = :categoria
            """
            result = conn.execute(text(query), {"user_id": user_id, "categoria": categoria})
            return [row[0] for row in result]
    except Exception as e:
        print(f"Erro ao obter fotos curtidas: {e}")
        return []


def is_photo_liked_by_user(user_id, photo_id):
    """Verificar se uma foto já foi curtida pelo usuário"""
    try:
        engine = get_engine('jdt')
        with engine.connect() as conn:
            query = """
                SELECT COUNT(*) 
                FROM JDT_EXTRA_KIDS_DAY_LIKES 
                WHERE user_id = :user_id AND photo_id = :photo_id
            """
            result = conn.execute(text(query), {"user_id": user_id, "photo_id": photo_id}).fetchone()
            return result[0] > 0 if result else False
    except Exception as e:
        print(f"Erro ao verificar curtida: {e}")
        return False