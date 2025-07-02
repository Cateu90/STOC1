from fastapi import FastAPI, Request, Form, status, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
import re
from repo.user_repo import UserRepo
from repo.categoria_repo import CategoriaRepo
from repo.produto_repo import ProdutoRepo
from repo.impressora_repo import ImpressoraRepo
from repo.comanda_repo import ComandaRepo
from repo.mesa_repo import MesaRepo
from repo.item_comanda_repo import ItemComandaRepo
from models.user import User
from models.categoria import Categoria
from models.produto import Produto
from models.mesa import Mesa
from models.impressora import Impressora
from models.comanda import Comanda
from models.item_comanda import ItemComanda
from util.auth import hash_password, verify_password
from util.permissions import require_role
from itsdangerous import URLSafeSerializer
import os
from pathlib import Path
from data.db import get_db
from datetime import date, datetime, timedelta
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from util.init_db import executar_sqls_iniciais
from jose import jwt
from fastapi.staticfiles import StaticFiles
from decimal import Decimal
from fastapi import Body
from typing import Any, Dict, List
from pydantic import BaseModel
import asyncio
import os
import platform
from services.print_service import PrintService
import traceback
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from util.network_info import get_ip_and_port


def json_serializable(data):
    if isinstance(data, list):
        return [json_serializable(item) for item in data]
    if isinstance(data, dict):
        return {key: json_serializable(value) for key, value in data.items()}
    if isinstance(data, (datetime, date)):
        return data.isoformat()
    if isinstance(data, Decimal):
        return float(data)
    return data

app = FastAPI()

def get_cors_origins():
    import os
    if os.getenv("ENVIRONMENT") == "development":
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://192.168.1.100:3000",
            "http://192.168.1.101:3000",
        ]
    elif os.getenv("ENVIRONMENT") == "production":
        return [
            "https://stoc.suaempresa.com",
            "https://app.stoc.suaempresa.com"
        ]
    else:
        return ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(), 
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=400)

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
api_router = APIRouter(prefix="/api")

SECRET_KEY = os.getenv("SECRET_KEY", "stoc-secret-key")
JWT_SECRET = os.getenv("JWT_SECRET", "stoc-jwt-secret")
JWT_ALGORITHM = "HS256"
session_serializer = URLSafeSerializer(SECRET_KEY)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

executar_sqls_iniciais("sql")

try:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT IGNORE INTO categorias (nome, impressora_id) VALUES ('PDV', NULL)")
    db.commit()
    cursor.close()
    db.close()
except Exception as e:
    print(f"[INFO] Categoria PDV já existe ou erro: {e}")

def criar_mesas_padrao(user_email):
    try:
        from repo.mesa_repo import MesaRepo
        mesas_existentes = MesaRepo.listar_mesas(user_email=user_email)
        
        print(f"[INFO] {len(mesas_existentes)} mesas encontradas para {user_email}")
        print(f"[INFO] Garçom pode cadastrar suas próprias mesas pelo app mobile")
        
    except Exception as e:
        print(f"[WARNING] Erro ao verificar mesas para {user_email}: {e}")

@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": None, "success": None})

@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": None, "success": None})

@app.post("/register", response_class=HTMLResponse)
def register(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...), confirm: str = Form(...)):
    if not name.strip():
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Nome é obrigatório!", "success": None})
    
    if not email.strip():
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "E-mail é obrigatório!", "success": None})
    
    if len(password) < 6:
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Senha deve ter pelo menos 6 caracteres!", "success": None})
    
    if password != confirm:
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "As senhas não coincidem!", "success": None})
    
    existing_user = UserRepo.get_user_by_email(email.lower())
    if existing_user:
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": f"E-mail {email} já está cadastrado! Use outro e-mail ou faça login.", "success": None})
    
    try:
        hashed = hash_password(password)
        user = User(name=name.strip(), email=email.lower().strip(), password=hashed, role="admin")
        UserRepo.create_user(user)
        from data.db import ensure_user_database_exists
        from util.init_db import executar_sqls_iniciais
        ensure_user_database_exists(email.lower().strip())
        executar_sqls_iniciais("sql", user_email=email.lower().strip())
        return RedirectResponse("/login?success=1", status_code=303)
    except Exception as e:
        print(f"[ERROR] Erro ao criar usuário: {e}")
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Erro interno. Tente novamente.", "success": None})

@app.post("/login", response_class=HTMLResponse)
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    if not email.strip():
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "E-mail é obrigatório!", "success": None})
    
    if not password.strip():
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Senha é obrigatória!", "success": None})
    
    user = UserRepo.get_user_by_email(email.lower().strip())
    if not user:
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "E-mail não encontrado! Verifique o e-mail ou crie uma conta.", "success": None})
    
    if not verify_password(password, user['password']):
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Senha incorreta! Tente novamente.", "success": None})
    
    try:
        from data.db import ensure_user_database_exists
        from util.init_db import executar_sqls_iniciais
        ensure_user_database_exists(user['email'])
        executar_sqls_iniciais("sql", user_email=user['email'])
        criar_mesas_padrao(user['email'])
    except Exception as e:
        print(f"[ERROR] Falha ao inicializar DB para {user['email']} no login: {e}")
        return templates.TemplateResponse("login_cadastro.html", {"request": request, "error": "Ocorreu um erro ao preparar sua conta. Tente novamente.", "success": None})

    session_data = session_serializer.dumps(user)
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie("session", session_data, max_age=86400, httponly=True)
    return response

@app.get("/logout")
def logout(response: Response):
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("session")
    return response

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    db = get_db(user['email'])
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as total FROM comandas WHERE status='aberta'")
    comandas_abertas = cursor.fetchone()["total"]
    hoje = date.today().strftime("%Y-%m-%d")
    cursor.execute("SELECT SUM(total) as vendas_hoje FROM comandas WHERE status='fechada' AND DATE(created_at) = %s", (hoje,))
    vendas_hoje = cursor.fetchone()["vendas_hoje"] or 0
    cursor.execute("SELECT COUNT(*) as total FROM produtos")
    produtos = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as total FROM impressoras")
    impressoras = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as total FROM mesas")
    mesas = cursor.fetchone()["total"]
    cursor.close()
    db.close()
    dashboard = {
        "comandas_abertas": comandas_abertas,
        "vendas_hoje": vendas_hoje,
        "produtos": produtos,
        "impressoras": impressoras,
        "mesas": mesas
    }
    from datetime import datetime
    now = datetime.now()
    ip, port = get_ip_and_port()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "dashboard": dashboard,
        "now": now,
        "backend_ip": ip,
        "backend_port": port
    })


@app.get("/pdv", response_class=HTMLResponse)
def pdv(request: Request):
    try:
        print("[DEBUG] Iniciando endpoint PDV")
        
        user = get_logged_user(request)
        print(f"[DEBUG] Usuário: {user}")
        
        if not user:
            print("[DEBUG] Usuário não logado, redirecionando")
            return RedirectResponse("/", status_code=302)
        
        print(f"[DEBUG] Buscando categorias para: {user['email']}")
        categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
        print(f"[DEBUG] Categorias encontradas: {len(categorias)}")
        
        categorias_unicas = []
        seen_nomes = set()
        for cat in categorias:
            if cat['nome'] not in seen_nomes:
                categorias_unicas.append(cat)
                seen_nomes.add(cat['nome'])
        if not any(cat['id'] == 0 for cat in categorias_unicas):
            categorias_unicas.insert(0, {"id": 0, "nome": "Sem Categoria"})
        
        print(f"[DEBUG] Buscando comandas abertas para: {user['email']}")
        comandas_abertas = ComandaRepo.listar_comandas_abertas(user_email=user['email'])
        print(f"[DEBUG] Comandas abertas: {len(comandas_abertas)}")

        print("[DEBUG] Renderizando template PDV")
        return templates.TemplateResponse("pdv.html", {
            "request": request,
            "user": user,
            "categorias": categorias_unicas,
            "comandas_abertas": comandas_abertas,
            "active_page": "pdv"
        })
    except Exception as e:
        print(f"[ERROR] Erro no endpoint PDV: {e}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": f"Erro interno do servidor: {str(e)}"
        }, status_code=500)


@app.get("/produtos", response_class=HTMLResponse)
def produtos(request: Request, page: int = 1, success: int = 0, deleted: int = 0):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    page_size = 20
    offset = (page - 1) * page_size
    produtos = ProdutoRepo.listar_produtos(offset=offset, limit=page_size, user_email=user['email'])
    total_produtos = ProdutoRepo.contar_produtos(user_email=user['email'])
    total_pages = (total_produtos + page_size - 1) // page_size
    categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
    categorias_unicas = []
    seen_ids = set()
    for cat in categorias:
        if cat['id'] not in seen_ids:
            categorias_unicas.append(cat)
            seen_ids.add(cat['id'])
    categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
    categorias_unicas = []
    seen_nomes = set()
    for cat in categorias:
        if cat['nome'] not in seen_nomes:
            categorias_unicas.append(cat)
            seen_nomes.add(cat['nome'])
    return templates.TemplateResponse("produtos.html", {
        "request": request,
        "produtos": produtos,
        "user": user,
        "active_page": "produtos",
        "page": page,
        "total_pages": total_pages,
        "success": success,
        "deleted": deleted,
        "categorias": categorias_unicas
    })

@app.get("/produtos/novo", response_class=HTMLResponse)
def produto_novo_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
    categorias_unicas = []
    seen_nomes = set()
    for cat in categorias:
        if cat['nome'].lower() == 'pdv':
            continue
        if cat['nome'] not in seen_nomes:
            categorias_unicas.append(cat)
            seen_nomes.add(cat['nome'])
    return templates.TemplateResponse("produto_novo.html", {"request": request, "categorias": categorias_unicas, "user": user})

@app.post("/produtos/novo", response_class=HTMLResponse)
def produto_novo(request: Request, nome: str = Form(...), preco: float = Form(...), categoria_id: int = Form(...), tipo: str = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    produto = Produto(nome=nome, preco=preco, categoria_id=categoria_id, tipo=tipo)
    try:
        ProdutoRepo.criar_produto(produto, user_email=user['email'])
        return RedirectResponse("/produtos?success=1", status_code=302)
    except Exception as e:
        print(f"[ERROR] Erro ao criar produto: {e}")
        categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
        return templates.TemplateResponse("produto_novo.html", {"request": request, "categorias": categorias, "user": user, "error": "Erro ao criar produto!"})

@app.post("/produtos/{produto_id}/excluir", response_class=HTMLResponse)
def produto_excluir(request: Request, produto_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    try:
        from repo.produto_repo import ProdutoRepo
        ProdutoRepo.excluir_produto(produto_id, user_email=user['email'])
        return RedirectResponse("/produtos?deleted=1", status_code=302)
    except Exception as e:
        error_message = f"Erro ao excluir produto: {e}"
        print(f"[ERROR] {error_message}")
        page_size = 20
        page = 1
        offset = (page - 1) * page_size
        produtos = ProdutoRepo.listar_produtos(offset=offset, limit=page_size, user_email=user['email'])
        total_produtos = ProdutoRepo.contar_produtos(user_email=user['email'])
        total_pages = (total_produtos + page_size - 1) // page_size
        categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
        categorias_unicas = []
        seen_ids = set()
        for cat in categorias:
            if cat['id'] not in seen_ids:
                categorias_unicas.append(cat)
                seen_ids.add(cat['id'])
    return templates.TemplateResponse("produtos.html", {
        "request": request, 
        "produtos": produtos, 
        "user": user, 
        "active_page": "produtos", 
        "error": error_message,
        "page": page,
        "total_pages": total_pages,
        "categorias": categorias_unicas,
        "success": 0,
        "deleted": 0
    })

@app.get("/produtos/{produto_id}/editar", response_class=HTMLResponse)
def produto_editar_form(request: Request, produto_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    produto = ProdutoRepo.get_produto_por_id(produto_id, user_email=user['email'])
    if not produto:
        return RedirectResponse("/produtos", status_code=302)
    
    categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
    categorias_unicas = []
    seen_nomes = set()
    for cat in categorias:
        if cat['nome'].lower() == 'pdv':
            continue
        if cat['nome'] not in seen_nomes:
            categorias_unicas.append(cat)
            seen_nomes.add(cat['nome'])
    return templates.TemplateResponse("produto_editar.html", {
        "request": request, 
        "produto": produto,
        "categorias": categorias_unicas, 
        "user": user
    })

@app.post("/produtos/{produto_id}/editar", response_class=HTMLResponse)
def produto_editar(request: Request, produto_id: int, nome: str = Form(...), preco: float = Form(...), categoria_id: int = Form(...), tipo: str = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    try:
        ProdutoRepo.editar_produto(produto_id, nome, preco, categoria_id, tipo, user_email=user['email'])
        return RedirectResponse("/produtos", status_code=302)
    except Exception as e:
        print(f"[ERROR] Erro ao editar produto: {e}")
        produto = ProdutoRepo.get_produto_por_id(produto_id, user_email=user['email'])
        categorias = CategoriaRepo.listar_categorias(user_email=user['email'])
        return templates.TemplateResponse("produto_editar.html", {"request": request, "produto": produto, "categorias": categorias, "user": user, "error": "Erro ao editar produto!"})

@app.get("/mesas", response_class=HTMLResponse)
def mesas(request: Request, success: int = 0, deleted: int = 0):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    try:
        mesas = MesaRepo.listar_mesas(user_email=user['email'])
        return templates.TemplateResponse("mesas.html", {
            "request": request,
            "mesas": mesas,
            "user": user,
            "active_page": "mesas",
            "success": success,
            "deleted": deleted
        })
    except Exception as e:
        print(f"[ERROR] Erro ao listar mesas: {e}")
        return templates.TemplateResponse("mesas.html", {
            "request": request,
            "mesas": [],
            "user": user,
            "active_page": "mesas",
            "error": f"Erro ao carregar mesas: {e}",
            "success": 0,
            "deleted": 0
        })

@app.get("/mesas/nova", response_class=HTMLResponse)
def mesa_nova_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("mesa_nova.html", {"request": request, "user": user})

@app.post("/mesas/nova", response_class=HTMLResponse)
def mesa_nova(request: Request, nome: str = Form(...), status: str = Form("disponivel")):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user['role'] != 'admin':
        return templates.TemplateResponse("mesa_nova.html", {
            "request": request,
            "user": user,
            "error": "Apenas administradores podem cadastrar mesas."
        })
    if not nome.strip():
        return templates.TemplateResponse("mesa_nova.html", {
            "request": request, 
            "user": user, 
            "error": "Nome da mesa é obrigatório!"
        })
    try:
        mesas_existentes = MesaRepo.listar_mesas(user_email=user['email'])
        for mesa in mesas_existentes:
            if mesa['nome'].lower() == nome.strip().lower():
                return templates.TemplateResponse("mesa_nova.html", {
                    "request": request, 
                    "user": user, 
                    "error": "Já existe uma mesa com esse nome!"
                })
        mesa = Mesa(nome=nome.strip(), status=status)
        MesaRepo.criar_mesa(mesa, user_email=user['email'])
        return RedirectResponse("/mesas?success=1", status_code=302)
    except Exception as e:
        print(f"[ERROR] Erro ao criar mesa: {e}")
        return templates.TemplateResponse("mesa_nova.html", {
            "request": request, 
            "user": user, 
            "error": f"Erro ao criar mesa: {e}"
        })

@app.get("/mesas/{mesa_id}/editar", response_class=HTMLResponse)
def mesa_editar_form(request: Request, mesa_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    try:
        mesa = MesaRepo.get_mesa_por_id(mesa_id, user_email=user['email'])
        if not mesa:
            return RedirectResponse("/mesas", status_code=302)
        
        return templates.TemplateResponse("mesa_editar.html", {
            "request": request, 
            "mesa": mesa,
            "user": user
        })
    except Exception as e:
        print(f"[ERROR] Erro ao buscar mesa para edição: {e}")
        return RedirectResponse("/mesas", status_code=302)

@app.post("/mesas/{mesa_id}/editar", response_class=HTMLResponse)
def mesa_editar(request: Request, mesa_id: int, nome: str = Form(...), status: str = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    if not nome.strip():
        mesa = MesaRepo.get_mesa_por_id(mesa_id, user_email=user['email'])
        return templates.TemplateResponse("mesa_editar.html", {
            "request": request, 
            "mesa": mesa,
            "user": user, 
            "error": "Nome da mesa é obrigatório!"
        })
    
    try:
        mesas_existentes = MesaRepo.listar_mesas(user_email=user['email'])
        for mesa in mesas_existentes:
            if mesa['id'] != mesa_id and mesa['nome'].lower() == nome.strip().lower():
                mesa_atual = MesaRepo.get_mesa_por_id(mesa_id, user_email=user['email'])
                return templates.TemplateResponse("mesa_editar.html", {
                    "request": request, 
                    "mesa": mesa_atual,
                    "user": user, 
                    "error": f"Já existe outra mesa com o nome '{nome.strip()}'"
                })
        
        MesaRepo.editar_mesa(mesa_id, nome.strip(), status, user_email=user['email'])
        return RedirectResponse("/mesas", status_code=302)
    except Exception as e:
        print(f"[ERROR] Erro ao editar mesa: {e}")
        mesa = MesaRepo.get_mesa_por_id(mesa_id, user_email=user['email'])
        return templates.TemplateResponse("mesa_editar.html", {
            "request": request, 
            "mesa": mesa,
            "user": user, 
            "error": f"Erro ao editar mesa: {e}"
        })

@app.post("/mesas/{mesa_id}/excluir", response_class=HTMLResponse)
def mesa_excluir(request: Request, mesa_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    try:
        MesaRepo.excluir_mesa(mesa_id, user_email=user['email'])
        return RedirectResponse("/mesas?deleted=1", status_code=302)
    except Exception as e:
        print(f"[ERROR] Erro ao excluir mesa: {e}")
        mesas = MesaRepo.listar_mesas(user_email=user['email'])
        return templates.TemplateResponse("mesas.html", {
            "request": request,
            "mesas": mesas,
            "user": user,
            "active_page": "mesas",
            "error": str(e),
            "success": 0,
            "deleted": 0
        })

@app.post("/mesas/{mesa_id}/status")
def mesa_alterar_status(request: Request, mesa_id: int, status: str = Body(..., embed=True)):
    user = get_logged_user(request)
    if not user:
        return JSONResponse({"error": "Não autorizado"}, status_code=401)
    
    status_validos = ['disponivel', 'ocupada', 'reservada']
    if status not in status_validos:
        return JSONResponse({"error": "Status inválido"}, status_code=400)
    
    try:
        mesa = MesaRepo.get_mesa_por_id(mesa_id, user_email=user['email'])
        if not mesa:
            return JSONResponse({"error": "Mesa não encontrada"}, status_code=404)
        MesaRepo.editar_mesa(mesa_id, mesa['nome'], status, user_email=user['email'])
        return JSONResponse({
            "success": True, 
            "message": f"Status da mesa alterado para {status}",
            "status": status
        })
    except Exception as e:
        print(f"[ERROR] Erro ao alterar status da mesa: {e}")
        return JSONResponse({"error": f"Erro ao alterar status: {e}"}, status_code=500)

@app.get("/categorias", response_class=HTMLResponse)
def categorias(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    categorias = [
        {"id": 1, "nome": "Comida"},
        {"id": 2, "nome": "Bebida"},
        {"id": 3, "nome": "Sobremesa"},
        {"id": 4, "nome": "PDV"},
        {"id": 5, "nome": "Outros"}
    ]
    return templates.TemplateResponse("categorias.html", {"request": request, "categorias": categorias, "user": user})

@app.get("/categorias/novo", response_class=HTMLResponse)
def categoria_nova_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    return RedirectResponse("/categorias", status_code=302)

@app.post("/categorias/novo", response_class=HTMLResponse)
def categoria_nova(request: Request, nome: str = Form(...), impressora_id: str = Form(None)):
    return RedirectResponse("/categorias", status_code=302)

@app.get("/impressoras", response_class=HTMLResponse)
def impressoras(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    impressoras = ImpressoraRepo.listar_impressoras(user_email=user['email'])
    return templates.TemplateResponse("impressoras.html", {"request": request, "impressoras": impressoras, "user": user})

@app.get("/impressoras/novo", response_class=HTMLResponse)
def impressora_nova_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    try:
        import win32print
        printers = [p[2] for p in win32print.EnumPrinters(2)]
    except ImportError:
        printers = ["Impressora1", "Impressora2"]
    categorias = [
        {"id": 1, "nome": "Comida"},
        {"id": 2, "nome": "Bebida"},
        {"id": 3, "nome": "Sobremesa"},
        {"id": 4, "nome": "PDV"},
        {"id": 5, "nome": "Outros"}
    ]
    return templates.TemplateResponse("impressora_nova.html", {"request": request, "user": user, "printers": printers, "categorias": categorias})

@app.post("/impressoras/novo", response_class=HTMLResponse)
def impressora_nova(request: Request, nome: str = Form(...), setor: str = Form(...), printer_name: str = Form(...), categorias: list = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    if not nome or not setor or not printer_name or not categorias:
        categorias_fixas = [
            {"id": 1, "nome": "Comida"},
            {"id": 2, "nome": "Bebida"},
            {"id": 3, "nome": "Sobremesa"},
            {"id": 4, "nome": "PDV"},
            {"id": 5, "nome": "Outros"}
        ]
        return templates.TemplateResponse("impressora_nova.html", {"request": request, "user": user, "error": "Preencha todos os campos!", "printers": [], "categorias": categorias_fixas})
    try:
        impressora = Impressora(nome=nome, setor=setor)
        impressora_id = ImpressoraRepo.criar_impressora_retorna_id(impressora, printer_name, user_email=user['email'])
        db = get_db(user['email'])
        cursor = db.cursor()
        for cat_id in categorias:
            cursor.execute("INSERT INTO impressora_categorias (impressora_id, categoria_id) VALUES (%s, %s)", (impressora_id, int(cat_id)))
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        categorias_fixas = [
            {"id": 1, "nome": "Comida"},
            {"id": 2, "nome": "Bebida"},
            {"id": 3, "nome": "Sobremesa"},
            {"id": 4, "nome": "PDV"},
            {"id": 5, "nome": "Outros"}
        ]
        return templates.TemplateResponse("impressora_nova.html", {"request": request, "user": user, "error": f"Erro ao adicionar impressora: {e}", "printers": [], "categorias": categorias_fixas})
    return RedirectResponse("/impressoras", status_code=302)

@app.post("/impressoras/{impressora_id}/excluir", response_class=HTMLResponse)
def impressora_excluir(request: Request, impressora_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    try:
        ImpressoraRepo.excluir_impressora(impressora_id, user_email=user['email'])
    except Exception as e:
        pass
    return RedirectResponse("/impressoras", status_code=302)

@app.get("/comandas", response_class=HTMLResponse)
def comandas(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    require_role(request, ["admin", "garcom"])
    
    if user['role'] == 'admin':
        comandas = ComandaRepo.listar_todas_comandas_admin(user['email'])
    else:
        comandas = ComandaRepo.listar_todas_comandas(user_email=user['email'])
    
    usuarios = UserRepo.listar_usuarios()
    garcons_dict = {u['id']: u['name'] for u in usuarios if u['role'] == 'garcom'}
    for c in comandas:
        c['garcom_nome'] = garcons_dict.get(c['garcom_id'], '---')
    return templates.TemplateResponse("comandas.html", {"request": request, "comandas": comandas, "user": user, "active_page": "comandas"})

@app.get("/comandas/nova", response_class=HTMLResponse)
def comanda_nova_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    mesas = MesaRepo.listar_mesas(user_email=user['email'])
    garcons = [u for u in UserRepo.listar_usuarios() if u['role'] == 'garcom']
    return templates.TemplateResponse("comanda_nova.html", {"request": request, "mesas": mesas, "garcons": garcons, "user": user})

@app.post("/comandas/nova", response_class=HTMLResponse)
def comanda_nova(request: Request, mesa_id: int = Form(...), garcom_id: int = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    comanda = Comanda(mesa_id=mesa_id, garcom_id=garcom_id, status="aberta")
    ComandaRepo.abrir_comanda(comanda, user_email=user['email'])
    import asyncio
    asyncio.create_task(notify_comandas_update())
    return RedirectResponse("/comandas", status_code=302)

@app.get("/comandas/{comanda_id}", response_class=HTMLResponse)
def comanda_itens(request: Request, comanda_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    try:
        comanda = ComandaRepo.get_comanda_por_id(comanda_id, user_email=user['email'])
        if not comanda:
            return RedirectResponse("/comandas", status_code=302)
        from repo.user_repo import UserRepo
        usuarios = UserRepo.listar_usuarios()
        garcons_dict = {u['id']: u['name'] for u in usuarios if u['role'] == 'garcom'}
        comanda['garcom_nome'] = garcons_dict.get(comanda.get('garcom_id'), '---')
        itens = ItemComandaRepo.listar_itens(comanda_id, user_email=user['email']) or []
        print(f"[DEBUG] Itens da comanda {comanda_id}: {itens}")
        produtos = ProdutoRepo.listar_produtos(user_email=user['email']) or []
        for item in itens:
            if 'produto_id' not in item:
                item['produto_id'] = None
            if 'quantidade' not in item:
                item['quantidade'] = 0
            if 'preco_unitario' not in item:
                item['preco_unitario'] = 0.0
        return templates.TemplateResponse("comanda_itens.html", {"request": request, "comanda": comanda, "itens": itens, "produtos": produtos, "user": user, "error": None, "status": comanda.get('status', '')})
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return templates.TemplateResponse("comanda_itens.html", {"request": request, "comanda": {}, "itens": [], "produtos": [], "user": user, "error": f"Erro interno: {e}\n{tb}"})

@app.post("/comandas/{comanda_id}", response_class=HTMLResponse)
def comanda_adicionar_item(request: Request, comanda_id: int, produto_id: int = Form(...), quantidade: int = Form(...)):
    print(f"[DEBUG] POST /comandas/{comanda_id} chamado com produto_id={produto_id}, quantidade={quantidade}")
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    produtos = ProdutoRepo.listar_produtos(user_email=user['email'])
    produto = next((p for p in produtos if p['id'] == produto_id), None)
    if not produto:
        return RedirectResponse(f"/comandas/{comanda_id}", status_code=302)
    item = ItemComanda(comanda_id=comanda_id, produto_id=produto_id, quantidade=quantidade, preco_unitario=produto['preco'])
    ItemComandaRepo.adicionar_item(item, user_email=user['email'])
    import asyncio
    asyncio.create_task(notify_comandas_update())
    return RedirectResponse(f"/comandas/{comanda_id}", status_code=302)

@app.get("/comandas/{comanda_id}/fechar", response_class=HTMLResponse)
def comanda_fechar_form(request: Request, comanda_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    comandas = ComandaRepo.listar_comandas_abertas(user_email=user['email'])
    comanda = next((c for c in comandas if c['id'] == comanda_id), None)
    if not comanda:
        return RedirectResponse("/comandas", status_code=302)
    itens = ItemComandaRepo.listar_itens(comanda_id, user_email=user['email'])
    return templates.TemplateResponse("comanda_fechar.html", {"request": request, "comanda": comanda, "itens": itens, "user": user})

@app.post("/comandas/{comanda_id}/fechar", response_class=HTMLResponse)
def comanda_fechar(request: Request, comanda_id: int, pagamento: str = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    
    db = get_db(user['email'])
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT SUM(quantidade * preco_unitario) as total 
        FROM itens_comanda 
        WHERE comanda_id = %s
    """, (comanda_id,))
    
    result = cursor.fetchone()
    total = result['total'] if result and result['total'] else 0.0
    
    cursor.execute("""
        UPDATE comandas 
        SET status='fechada', total=%s, pagamento=%s 
        WHERE id=%s
    """, (total, pagamento, comanda_id))
    
    db.commit()
    cursor.close()
    db.close()
    import asyncio
    asyncio.create_task(notify_comandas_update())
    return RedirectResponse("/comandas", status_code=302)

@app.get("/relatorios", response_class=HTMLResponse)
def relatorios(request: Request, inicio: str = None, fim: str = None):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    if not inicio or not fim:
        hoje = date.today()
        inicio = hoje.strftime("%Y-%m-%d")
        fim = hoje.strftime("%Y-%m-%d")
    
    db = get_db(user['email'])
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT c.id, c.garcom_id, c.pagamento, c.total, c.created_at 
        FROM comandas c 
        WHERE c.status='fechada' AND DATE(c.created_at) BETWEEN %s AND %s 
        ORDER BY c.created_at DESC
    """, (inicio, fim))
    comandas = cursor.fetchall()
    
    cursor.execute("""
        SELECT p.nome as produto_nome, SUM(ic.quantidade) as total_vendido, 
               SUM(ic.quantidade * ic.preco_unitario) as total_faturado
        FROM itens_comanda ic 
        JOIN comandas c ON ic.comanda_id = c.id 
        JOIN produtos p ON ic.produto_id = p.id
        WHERE c.status='fechada' AND DATE(c.created_at) BETWEEN %s AND %s 
        GROUP BY ic.produto_id, p.nome 
        ORDER BY total_vendido DESC 
        LIMIT 10
    """, (inicio, fim))
    mais_vendidos = cursor.fetchall()
    
    cursor.execute("""
        SELECT c.garcom_id, COUNT(*) as comandas, SUM(c.total) as total_vendas 
        FROM comandas c 
        WHERE c.status='fechada' AND DATE(c.created_at) BETWEEN %s AND %s 
        GROUP BY c.garcom_id 
        ORDER BY total_vendas DESC
    """, (inicio, fim))
    ranking = cursor.fetchall()
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total_comandas,
            SUM(total) as faturamento_total,
            AVG(total) as ticket_medio
        FROM comandas 
        WHERE status='fechada' AND DATE(created_at) BETWEEN %s AND %s
    """, (inicio, fim))
    estatisticas = cursor.fetchone()
    
    cursor.close()
    db.close()
    
    from repo.user_repo import UserRepo
    usuarios = UserRepo.listar_usuarios()
    garcons_dict = {u['id']: u['name'] for u in usuarios if u['role'] == 'garcom'}
    for c in comandas:
        c['garcom_nome'] = garcons_dict.get(c['garcom_id'], '---')
    for r in ranking:
        r['garcom_nome'] = garcons_dict.get(r['garcom_id'], '---')
    
    return templates.TemplateResponse("relatorios.html", {
        "request": request, 
        "comandas": comandas,
        "mais_vendidos": mais_vendidos,
        "ranking": ranking,
        "estatisticas": estatisticas,
        "inicio": inicio,
        "fim": fim,
        "user": user
    })

@app.get("/usuarios", response_class=HTMLResponse)
def usuarios(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    if user['role'] == 'admin':
        usuarios = [u for u in UserRepo.listar_usuarios() if u.get('admin_id') == user['id'] and u['role'] == 'garcom']
    else:
        usuarios = [user]
    return templates.TemplateResponse("usuarios.html", {"request": request, "usuarios": usuarios, "user": user, "active_page": "usuarios"})

@app.get("/usuarios/novo", response_class=HTMLResponse)
def usuario_novo_form(request: Request):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    return templates.TemplateResponse("usuario_novo.html", {"request": request, "user": user, "active_page": "usuarios"})

@app.post("/usuarios/novo", response_class=HTMLResponse)
def usuario_novo(request: Request, name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    if not name or not email or not password:
        return templates.TemplateResponse("usuario_novo.html", {"request": request, "user": user, "active_page": "usuarios", "error": "Preencha todos os campos!"})
    if UserRepo.get_user_by_email(email.lower()):
        return templates.TemplateResponse("usuario_novo.html", {"request": request, "user": user, "active_page": "usuarios", "error": "E-mail já cadastrado!"})
    from util.auth import hash_password
    hashed = hash_password(password)
    admin_id = user['id'] if user['role'] == 'admin' else None
    novo = User(name=name, email=email.lower(), password=hashed, role="garcom", admin_id=admin_id)
    try:
        UserRepo.create_user(novo)
    except Exception as e:
        return templates.TemplateResponse("usuario_novo.html", {"request": request, "user": user, "active_page": "usuarios", "error": f"Erro ao cadastrar usuário: {e}"})
    return RedirectResponse("/usuarios", status_code=302)

@app.post("/usuarios/{usuario_id}/excluir", response_class=HTMLResponse)
def usuario_excluir(request: Request, usuario_id: int):
    user = get_logged_user(request)
    if not user:
        return RedirectResponse("/", status_code=302)
    UserRepo.excluir_usuario(usuario_id)
    return RedirectResponse("/usuarios", status_code=302)

def get_logged_user_api(request: Request) -> Dict[str, Any]:
    session_token = request.cookies.get("session")
    if not session_token:
        return None
    try:
        user_data = session_serializer.loads(session_token)
        return user_data
    except Exception:
        return None

class ItemVenda(BaseModel):
    id: int
    qtd: int
    preco: float

class Venda(BaseModel):
    itens: List[ItemVenda]
    pagamento: str

@api_router.delete("/produtos/{produto_id}")
def api_delete_produto(request: Request, produto_id: int):
    user = get_logged_user_api(request)
    if not user:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"success": False, "message": "Não autorizado"})
    
    try:
        produto = ProdutoRepo.get_produto_por_id(produto_id, user_email=user['email'])
        if not produto:
            return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"success": False, "message": "Produto não encontrado"})

        ProdutoRepo.excluir_produto(produto_id, user_email=user['email'])
        return JSONResponse(status_code=status.HTTP_200_OK, content={"success": True, "message": "Produto desativado com sucesso"})
    except Exception as e:
        print(f"[ERROR] Erro ao desativar produto via API: {e}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"success": False, "message": f"Erro interno no servidor: {e}"})

@api_router.post("/pdv/venda")
async def api_pdv_venda(request: Request, venda: Venda):
    user = get_logged_user_api(request)
    if not user:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Não autorizado"})

    print(f"[DEBUG] Venda recebida: {venda}")
    print(f"[DEBUG] Itens recebidos: {getattr(venda, 'itens', None)}")

    db = None
    try:
        impressora_pdv = ImpressoraRepo.get_impressora_por_nome_categoria("PDV", user_email=user['email'])
        if not impressora_pdv:
            print("[INFO] Impressora PDV não encontrada. Tentando criar automaticamente...")
            try:
                import win32print
                impressoras_sistema = [p[2] for p in win32print.EnumPrinters(2)]
                impressora_padrao = win32print.GetDefaultPrinter() if impressoras_sistema else "Impressora_PDV"
            except ImportError:
                impressora_padrao = "Impressora_PDV"
                impressoras_sistema = [impressora_padrao]
            
            try:
                from models.impressora import Impressora
                impressora_obj = Impressora(nome="PDV", setor="PDV")
                impressora_id = ImpressoraRepo.criar_impressora_retorna_id(impressora_obj, impressora_padrao, user_email=user['email'])
                
                db_temp = get_db(user['email'])
                cursor_temp = db_temp.cursor()
                
                cursor_temp.execute("SELECT id FROM categorias WHERE nome = 'PDV'")
                categoria_pdv = cursor_temp.fetchone()
                
                if categoria_pdv:
                    categoria_id = categoria_pdv[0]
                else:
                    cursor_temp.execute("INSERT INTO categorias (nome, impressora_id) VALUES ('PDV', NULL)")
                    categoria_id = cursor_temp.lastrowid
                
                cursor_temp.execute("INSERT INTO impressora_categorias (impressora_id, categoria_id) VALUES (%s, %s)", (impressora_id, categoria_id))
                db_temp.commit()
                cursor_temp.close()
                db_temp.close()
                
                print(f"[INFO] Impressora PDV criada automaticamente: {impressora_padrao}")
                
                impressora_pdv = ImpressoraRepo.get_impressora_por_nome_categoria("PDV", user_email=user['email'])
                
            except Exception as e:
                print(f"[ERROR] Erro ao criar impressora PDV automaticamente: {e}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": f"Impressora não configurada para o PDV e não foi possível criar automaticamente. Erro: {str(e)}"}
                )
        
        if not impressora_pdv:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Impressora não configurada para o PDV. Por favor, cadastre uma impressora e associe-a à categoria 'PDV' nas configurações."}
            )

        db = get_db(user['email'])
        cursor = db.cursor(dictionary=True)
        db.start_transaction()

        from util.numero_comanda_global import get_proximo_numero_comanda
        numero_comanda = get_proximo_numero_comanda()

        pdv_user = UserRepo.get_user_by_name("PDV", user_email=user['email'])
        garcom_id = pdv_user['id'] if pdv_user else None
        if not garcom_id:
            garcom_id = user['id']
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = DATABASE() 
              AND TABLE_NAME = 'comandas' 
              AND COLUMN_NAME = 'numero'
        """)
        result = cursor.fetchone()
        coluna_numero_existe = result['count'] if result else 0
        
        if coluna_numero_existe > 0:
            sql_comanda = "INSERT INTO comandas (numero, garcom_id, status) VALUES (%s, %s, %s)"
            cursor.execute(sql_comanda, (numero_comanda, garcom_id, "aberta"))
        else:
            print(f"[WARNING] Coluna 'numero' não existe. Usando apenas ID para comanda PDV.")
            sql_comanda = "INSERT INTO comandas (garcom_id, status) VALUES (%s, %s)"
            cursor.execute(sql_comanda, (garcom_id, "aberta"))
        
        comanda_id = cursor.lastrowid
        
        print(f"[INFO] Comanda PDV criada - ID: {comanda_id}, Número: {numero_comanda}")

        total_venda = Decimal(0)
        itens_para_impressao = []
        for item in venda.itens:
            produto_db = ProdutoRepo.get_produto_por_id(item.id, user_email=user['email'])
            if not produto_db:
                db.rollback()
                return JSONResponse(status_code=404, content={"error": f"Produto com ID {item.id} não encontrado."})
            preco_unitario = Decimal(produto_db['preco'])
            item_comanda = ItemComanda(
                comanda_id=comanda_id,
                produto_id=item.id,
                quantidade=item.qtd,
                preco_unitario=preco_unitario
            )
            ItemComandaRepo.adicionar_item(item_comanda, db=db, cursor=cursor)
            total_venda += item.qtd * preco_unitario
            itens_para_impressao.append({"nome": produto_db['nome'], "qtd": item.qtd, "preco": preco_unitario})

        ComandaRepo.fechar_comanda(comanda_id, total_venda, venda.pagamento, db=db, cursor=cursor)
        db.commit()

        texto_comprovante = gerar_texto_comprovante(comanda_id, itens_para_impressao, total_venda, venda.pagamento, numero_comanda)
        
        print(f"[DEBUG] Impressora PDV encontrada: {impressora_pdv}")
        print(f"[DEBUG] Nome da impressora: {impressora_pdv.get('printer_name', 'N/A')}")
        print(f"[DEBUG] Texto do comprovante:\n{texto_comprovante}")
        
        resultado_impressao = PrintService.imprimir_texto(texto_comprovante, impressora_pdv['printer_name'])
        
        print(f"[DEBUG] Resultado da impressão: {resultado_impressao}")
        
        status_impressao = ""
        if resultado_impressao["status"] == "success":
            status_impressao = "Comprovante impresso com sucesso"
            print(f"[INFO] Comprovante da venda #{numero_comanda} (ID: {comanda_id}) enviado para a impressora {impressora_pdv['printer_name']}.")
        else:
            status_impressao = f"Falha ao imprimir: {resultado_impressao['message']}"
            print(f"[ERROR] Falha ao imprimir comprovante da venda #{numero_comanda} (ID: {comanda_id}): {resultado_impressao['message']}")

        return JSONResponse(content={
            "success": True, 
            "comanda_id": comanda_id, 
            "numero_comanda": numero_comanda,
            "message": f"Venda finalizada com sucesso! Comanda #{numero_comanda}", 
            "print_status": status_impressao
        })

    except Exception as e:
        if db is not None:
            try:
                db.rollback()
            except Exception:
                pass
        print(f"[ERROR] Erro ao finalizar venda direta no PDV: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": "Erro interno ao processar a venda."})
    finally:
        try:
            if 'cursor' in locals() and cursor:
                cursor.close()
        except Exception:
            pass
        try:
            if db is not None and db.is_connected():
                db.close()
        except Exception:
            pass

def gerar_texto_comprovante(comanda_id, itens, total, pagamento, numero_comanda=None):
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    texto = f"COMPROVANTE DE VENDA\n"
    
    if numero_comanda:
        texto += f"Comanda: #{numero_comanda}\n"
    else:
        texto += f"Comanda: #{comanda_id}\n"
        
    texto += f"Data: {now}\n"
    texto += "-" * 30 + "\n"
    texto += "Qtd  Produto             Preco\n"
    for item in itens:
        nome_produto = item['nome'][:18].ljust(18)
        preco_str = f"R$ {item['preco']:.2f}".rjust(7)
        texto += f"{item['qtd']:<3} {nome_produto} {preco_str}\n"
    texto += "-" * 30 + "\n"
    texto += f"TOTAL: R$ {total:.2f}\n"
    texto += f"PAGAMENTO: {pagamento.upper()}\n\n"
    texto += "Obrigado!\n"
    return texto

def gerar_texto_pedido_item(comanda_id, produto, quantidade):
    from datetime import datetime
    
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    texto = f"PEDIDO - COMANDA #{comanda_id}\n"
    texto += f"Data: {now}\n"
    texto += "-" * 30 + "\n"
    texto += f"{quantidade}x {produto['nome']}\n"
    texto += f"Preco: R$ {produto['preco']:.2f}\n"
    texto += "-" * 30 + "\n"
    texto += "COZINHA\n\n"
    
    return texto

@api_router.get("/produtos/{categoria_id}")
def api_get_produtos_por_categoria(request: Request, categoria_id: str):
    user = get_logged_user_api(request)
    if not user:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"error": "Não autorizado"})
    
    try:
        user_email = user['email']
        user_role = user['role']
        
        print(f"[INFO] Listando produtos da categoria {categoria_id} para usuário: {user_email} (role: {user_role})")
        
        from repo.user_repo import UserRepo
        
        if user_role == "garcom":
            admin_email = UserRepo.get_admin_email_for_garcom(user_email)
            search_user_email = admin_email if admin_email else None
        else:
            search_user_email = user_email
        
        if categoria_id.lower() == 'all':
            produtos = ProdutoRepo.listar_produtos(user_email=search_user_email)
        elif categoria_id.lower() == 'sem-categoria':
            produtos = ProdutoRepo.listar_produtos_sem_categoria(user_email=search_user_email)
        else:
            produtos = ProdutoRepo.listar_produtos_por_categoria(int(categoria_id), user_email=search_user_email)
        
        print(f"[SUCCESS] {len(produtos)} produtos encontrados na categoria {categoria_id} para {user_email}")
        
        return JSONResponse(content=json_serializable(produtos))
    except Exception as e:
        print(f"[ERROR] Erro ao buscar produtos por categoria via API: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: str
    password: str

@api_router.post("/login")
async def api_login(login_data: LoginRequest):
    try:
        print(f"[INFO] Tentativa de login para: {login_data.email}")
        
        user = UserRepo.get_user_by_email(login_data.email)
        from util.auth import verify_password
        
        if not user:
            print(f"[WARNING] Usuário não encontrado: {login_data.email}")
            return JSONResponse({"error": "Credenciais inválidas."}, status_code=401)
        
        if not verify_password(login_data.password, user['password']):
            print(f"[WARNING] Senha incorreta para: {login_data.email}")
            return JSONResponse({"error": "Credenciais inválidas."}, status_code=401)
        
        if user['role'] not in ['admin', 'garcom']:
            print(f"[WARNING] Role não autorizado: {user['role']} para {login_data.email}")
            return JSONResponse({"error": "Usuário não autorizado para o app mobile."}, status_code=401)
        
        from util.mobile_utils import get_banco_usuario_para_mobile
        banco_usuario = get_banco_usuario_para_mobile(user['email'], user['role'])
        
        if user['role'] == 'garcom':
            try:
                print(f"[INFO] Inicializando ambiente para garçom: {login_data.email} (banco: {banco_usuario})")
                from data.db import ensure_user_database_exists
                from util.init_db import executar_sqls_iniciais
                
                ensure_user_database_exists(banco_usuario)
                
                executar_sqls_iniciais("sql", user_email=banco_usuario)
                
                try:
                    db_centralizado = get_db(banco_usuario)
                    cursor_central = db_centralizado.cursor(dictionary=True)
                    
                    cursor_central.execute("SELECT id FROM users WHERE email = %s", (user['email'],))
                    garcom_existente = cursor_central.fetchone()
                    
                    if not garcom_existente:
                        print(f"[INFO] Criando registro do garçom {user['email']} no banco centralizado")
                        
                        cursor_central.execute("""
                            INSERT INTO users (name, email, password, role, admin_id, created_at) 
                            VALUES (%s, %s, %s, %s, (SELECT id FROM users WHERE role='admin' LIMIT 1), NOW())
                        """, (user['name'], user['email'], user['password'], user['role']))
                        
                        garcom_id_centralizado = cursor_central.lastrowid
                        db_centralizado.commit()
                        
                        print(f"[SUCCESS] Garçom {user['email']} criado no banco centralizado com ID: {garcom_id_centralizado}")
                    else:
                        print(f"[INFO] Garçom {user['email']} já existe no banco centralizado com ID: {garcom_existente['id']}")
                    
                    cursor_central.close()
                    db_centralizado.close()
                    
                except Exception as sync_error:
                    print(f"[ERROR] Erro ao sincronizar garçom no banco centralizado: {sync_error}")
                
                print(f"[SUCCESS] Ambiente inicializado para garçom: {login_data.email} (banco: {banco_usuario})")
                
            except Exception as e:
                print(f"[ERROR] Erro ao inicializar ambiente para garçom {login_data.email}: {e}")
                import traceback
                traceback.print_exc()
                return JSONResponse({"error": "Erro ao preparar seu ambiente. Tente novamente."}, status_code=500)
        
        token_data = {
            "id": user['id'], 
            "email": user['email'], 
            "role": user['role'],
            "banco_usuario": banco_usuario
        }
        token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
        
        print(f"[SUCCESS] Login bem-sucedido para: {login_data.email} (banco: {banco_usuario})")
        return {
            "token": token, 
            "id": user['id'], 
            "name": user['name'], 
            "role": user['role'],
            "banco_usuario": banco_usuario
        }
        
    except Exception as e:
        print(f"[ERROR] Erro no login para {login_data.email}: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": "Erro interno do servidor"}, status_code=500)

@api_router.get("/mesas")
def api_listar_mesas(request: Request):
    user_payload, banco_usuario = get_user_and_banco_from_token(request)
    if not user_payload or not banco_usuario:
        return JSONResponse({"error": "Token de autorização necessário"}, status_code=401)
    
    try:
        user_email = user_payload.get("email")
        user_role = user_payload.get("role")
        
        print(f"[INFO] Listando mesas para usuário: {user_email} (role: {user_role}, banco: {banco_usuario})")
        
        try:
            from repo.mesa_repo import MesaRepo
            
            mesas = MesaRepo.listar_mesas(user_email=banco_usuario)
            print(f"[SUCCESS] {len(mesas)} mesas encontradas para {user_email} (banco: {banco_usuario})")
            
            return mesas
            
        except Exception as mesa_error:
            print(f"[WARNING] Erro ao listar mesas para {user_email}: {mesa_error}")
            print(f"[INFO] Retornando lista vazia")
            return []
        
    except Exception as e:
        print(f"[ERROR] Erro crítico ao listar mesas: {e}")
        import traceback
        traceback.print_exc()
        return []

@api_router.post("/mesas")
async def api_cadastrar_mesa(request: Request, nome: str = Form(...)):
    user_payload, banco_usuario = get_user_and_banco_from_token(request)
    if not user_payload or not banco_usuario:
        return JSONResponse({"error": "Token de autorização necessário"}, status_code=401)
    
    try:
        user_email = user_payload.get("email")
        user_role = user_payload.get("role")
        
        print(f"[INFO] Cadastrando nova mesa '{nome}' para usuário: {user_email} (role: {user_role}, banco: {banco_usuario})")
        
        if not nome or not nome.strip():
            return JSONResponse({"error": "Nome da mesa é obrigatório"}, status_code=400)
        
        nome = nome.strip()
        
        try:
            from data.db import ensure_user_database_exists
            from util.init_db import executar_sqls_iniciais
            
            ensure_user_database_exists(banco_usuario)
            executar_sqls_iniciais("sql", user_email=banco_usuario)
            
        except Exception as setup_error:
            print(f"[ERROR] Erro crítico ao configurar ambiente para {banco_usuario}: {setup_error}")
            return JSONResponse({"error": "Erro ao configurar ambiente. Tente novamente."}, status_code=500)
        
        try:
            from repo.mesa_repo import MesaRepo
            mesas_existentes = MesaRepo.listar_mesas(user_email=banco_usuario)
            
            for mesa in mesas_existentes:
                if mesa['nome'].lower() == nome.lower():
                    return JSONResponse({"error": f"Já existe uma mesa com o nome '{nome}'"}, status_code=400)
        except Exception as check_error:
            print(f"[WARNING] Erro ao verificar mesas existentes: {check_error}")
        
        try:
            db = get_db(banco_usuario)
            cursor = db.cursor()
            cursor.execute("INSERT INTO mesas (nome) VALUES (%s)", (nome,))
            mesa_id = cursor.lastrowid
            db.commit()
            cursor.close()
            db.close()
            
            print(f"[SUCCESS] Mesa '{nome}' cadastrada com sucesso no banco {banco_usuario}")
            
            return JSONResponse({
                "success": True,
                "message": f"Mesa '{nome}' cadastrada com sucesso!",
                "mesa": {
                    "id": mesa_id,
                    "nome": nome
                }
            })
        except Exception as db_error:
            print(f"[ERROR] Erro ao cadastrar mesa no banco: {db_error}")
            return JSONResponse({"error": "Erro ao salvar mesa no banco de dados"}, status_code=500)
        
    except Exception as e:
        print(f"[ERROR] Erro ao cadastrar mesa: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": "Erro interno do servidor"}, status_code=500)

@api_router.delete("/mesas/{mesa_id}")
async def api_excluir_mesa(request: Request, mesa_id: int):
    user_payload, banco_usuario = get_user_and_banco_from_token(request)
    if not user_payload or not banco_usuario:
        return JSONResponse({"error": "Token de autorização necessário"}, status_code=401)
    
    try:
        user_email = user_payload.get("email")
        user_role = user_payload.get("role")
        
        print(f"[INFO] Excluindo mesa ID {mesa_id} para usuário: {user_email} (role: {user_role}, banco: {banco_usuario})")
        
        from repo.mesa_repo import MesaRepo
        mesas = MesaRepo.listar_mesas(user_email=banco_usuario)
        mesa_encontrada = None
        for mesa in mesas:
            if mesa['id'] == mesa_id:
                mesa_encontrada = mesa
                break
        
        if not mesa_encontrada:
            return JSONResponse({"error": "Mesa não encontrada"}, status_code=404)
        
        db = get_db(banco_usuario)
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) as total FROM comandas WHERE mesa_id = %s AND status = 'aberta'", (mesa_id,))
        result = cursor.fetchone()
        
        if result and result['total'] > 0:
            cursor.close()
            db.close()
            return JSONResponse({"error": "Não é possível excluir uma mesa com comandas abertas"}, status_code=400)
        
        cursor.execute("DELETE FROM mesas WHERE id = %s", (mesa_id,))
        db.commit()
        cursor.close()
        db.close()
        
        print(f"[SUCCESS] Mesa '{mesa_encontrada['nome']}' excluída com sucesso do banco {banco_usuario}")
        
        return JSONResponse({
            "success": True,
            "message": f"Mesa '{mesa_encontrada['nome']}' excluída com sucesso!"
        })
        
    except Exception as e:
        print(f"[ERROR] Erro ao excluir mesa: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": "Erro interno do servidor"}, status_code=500)

@api_router.get("/mesas/{mesa_id}/comanda")
def api_verificar_comanda_mesa(request: Request, mesa_id: int):
    user_payload, banco_usuario = get_user_and_banco_from_token(request)
    if not user_payload or not banco_usuario:
        return JSONResponse({"error": "Token de autorização necessário"}, status_code=401)
    
    try:
        user_email = user_payload.get("email")
        user_role = user_payload.get("role")
        
        print(f"[INFO] Verificando comanda da mesa {mesa_id} para usuário: {user_email} (role: {user_role}, banco: {banco_usuario})")
        
        from repo.comanda_repo import ComandaRepo
        
        comandas = ComandaRepo.listar_comandas_por_mesa(mesa_id, user_email=banco_usuario)
        comanda_aberta = None
        
        for comanda in comandas:
            if comanda.get('status') != 'fechada':
                comanda_aberta = comanda
                break
        
        if comanda_aberta:
            numero_exibicao = comanda_aberta.get('numero_exibicao') or comanda_aberta.get('numero') or comanda_aberta['id']
            print(f"[INFO] Mesa {mesa_id} tem comanda aberta: #{numero_exibicao} (ID: {comanda_aberta['id']}) no banco {banco_usuario}")
            return JSONResponse({
                "success": True,
                "comanda": {
                    "id": comanda_aberta['id'],
                    "numero": comanda_aberta.get('numero'),
                    "numero_exibicao": numero_exibicao,
                    "mesa_id": mesa_id,
                    "status": comanda_aberta.get('status', 'aberta'),
                    "data_abertura": comanda_aberta.get('data_abertura', '').isoformat() if comanda_aberta.get('data_abertura') else None
                }
            })
        else:
            print(f"[INFO] Mesa {mesa_id} está livre no banco {banco_usuario}")
            return JSONResponse({
                "success": True,
                "comanda": None
            })
            
    except Exception as e:
        print(f"[ERROR] Erro ao verificar comanda da mesa: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": "Erro interno do servidor"}, status_code=500)

@api_router.post("/comandas/abrir")
async def api_comanda_abrir(request: Request):
    user = get_logged_user_api(request)
    if not user:
        return JSONResponse(status_code=401, content={"success": False, "error": "Não autorizado"})
    try:
        data = await request.json()
        mesa_id = data.get("mesa_id")
        itens = data.get("itens", [])
        pagamento = data.get("pagamento", "")
        if not mesa_id or not itens:
            return JSONResponse(status_code=400, content={"success": False, "error": "Dados incompletos"})
        from models.comanda import Comanda
        from models.item_comanda import ItemComanda
        from repo.comanda_repo import ComandaRepo
        from repo.item_comanda_repo import ItemComandaRepo
        from repo.produto_repo import ProdutoRepo
        from repo.user_repo import UserRepo
        from repo.impressora_repo import ImpressoraRepo
        db = get_db(user['email'])
        cursor = db.cursor(dictionary=True)
        db.start_transaction()
        garcom = UserRepo.get_user_by_email(user['email'], user_email=user['email'])
        if not garcom:
            from util.auth import hash_password
            hashed = hash_password(user['email'])
            from models.user import User
            admin_id = None
            if 'admin_id' in user:
                admin_id = user['admin_id']
            novo = User(name=user['name'], email=user['email'], password=hashed, role="garcom", admin_id=admin_id)
            garcom_id = UserRepo.create_user(novo, user_email=user['email'])
        else:
            garcom_id = garcom['id']
        comanda = Comanda(mesa_id=mesa_id, garcom_id=garcom_id, status="aberta")
        comanda_id = ComandaRepo.abrir_comanda(comanda, user_email=user['email'])
        total = Decimal(0)
        itens_para_impressao = []
        for item in itens:
            produto_db = ProdutoRepo.get_produto_por_id(item['id'], user_email=user['email'])
            if not produto_db:
                db.rollback()
                return JSONResponse(status_code=404, content={"success": False, "error": f"Produto {item['id']} não encontrado"})
            preco_unitario = Decimal(produto_db['preco'])
            item_comanda = ItemComanda(comanda_id=comanda_id, produto_id=item['id'], quantidade=item['qtd'], preco_unitario=preco_unitario)
            ItemComandaRepo.adicionar_item(item_comanda, db=db, cursor=cursor)
            total += item['qtd'] * preco_unitario
            itens_para_impressao.append({"nome": produto_db['nome'], "qtd": item['qtd'], "preco": preco_unitario})
        db.commit()
        texto_comprovante = gerar_texto_comprovante(comanda_id, itens_para_impressao, total, pagamento)
        impressora = ImpressoraRepo.get_impressora_por_nome_categoria(produto_db['categoria_id'], user_email=user['email'])
        if impressora:
            PrintService.imprimir_texto(texto_comprovante, impressora['printer_name'])
        return JSONResponse(content={"success": True, "comanda_id": comanda_id, "message": "Pedido enviado e impresso!"})
    except Exception as e:
        print(f"[ERROR] Erro ao abrir comanda via API: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "error": "Erro interno ao abrir comanda."})

app.include_router(api_router)

class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/comandas")
async def websocket_comandas(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast("update")

async def notify_comandas_update():
    await manager.broadcast("update")

def get_logged_user(request: Request):
    if 'user' in request.scope:
        return request.scope.get('user')
    
    session_data = request.cookies.get("session")
    if not session_data:
        request.scope['user'] = None
        return None
    try:
        user_data = session_serializer.loads(session_data)
        request.scope['user'] = user_data
        return user_data
    except Exception:
        request.scope['user'] = None
        return None

@app.get("/mesas/{mesa_id}/comanda")
def api_verificar_comanda_mesa(request: Request, mesa_id: int):
    user_payload, banco_usuario = get_user_and_banco_from_token(request)
    if not user_payload or not banco_usuario:
        return JSONResponse({"error": "Token de autorização necessário"}, status_code=401)
    
    try:
        user_email = user_payload.get("email")
        user_role = user_payload.get("role")
        
        print(f"[INFO] Verificando comanda da mesa {mesa_id} para usuário: {user_email} (role: {user_role}, banco: {banco_usuario})")
        
        from repo.comanda_repo import ComandaRepo
        
        comandas = ComandaRepo.listar_comandas_por_mesa(mesa_id, user_email=banco_usuario)
        comanda_aberta = None
        
        for comanda in comandas:
            if comanda.get('status') != 'fechada':
                comanda_aberta = comanda
                break
        
        if comanda_aberta:
            numero_exibicao = comanda_aberta.get('numero_exibicao') or comanda_aberta.get('numero') or comanda_aberta['id']
            print(f"[INFO] Mesa {mesa_id} tem comanda aberta: #{numero_exibicao} (ID: {comanda_aberta['id']}) no banco {banco_usuario}")
            return JSONResponse({
                "success": True,
                "comanda": {
                    "id": comanda_aberta['id'],
                    "numero": comanda_aberta.get('numero'),
                    "numero_exibicao": numero_exibicao,
                    "mesa_id": mesa_id,
                    "status": comanda_aberta.get('status', 'aberta'),
                    "data_abertura": comanda_aberta.get('data_abertura', '').isoformat() if comanda_aberta.get('data_abertura') else None
                }
            })
        else:
            print(f"[INFO] Mesa {mesa_id} está livre no banco {banco_usuario}")
            return JSONResponse({
                "success": True,
                "comanda": None
            })
            
    except Exception as e:
        print(f"[ERROR] Erro ao verificar comanda da mesa: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": "Erro interno do servidor"}, status_code=500)

@api_router.get("/comandas/{comanda_id}/itens")
def api_listar_itens_comanda(request: Request, comanda_id: int):
    user_payload, banco_usuario = get_user_and_banco_from_token(request)
    if not user_payload or not banco_usuario:
        return JSONResponse({"error": "Token de autorização necessário"}, status_code=401)
    
    try:
        user_email = user_payload.get("email")
        user_role = user_payload.get("role")
        
        print(f"[INFO] Listando itens da comanda {comanda_id} para usuário: {user_email} (role: {user_role}, banco: {banco_usuario})")
        
        from repo.item_comanda_repo import ItemComandaRepo
        
        itens = ItemComandaRepo.listar_itens_por_comanda(comanda_id, user_email=banco_usuario)
        
        print(f"[SUCCESS] {len(itens)} itens encontrados na comanda {comanda_id} (banco: {banco_usuario})")
        
        return JSONResponse(content=json_serializable(itens))
        
    except Exception as e:
        print(f"[ERROR] Erro ao listar itens da comanda: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": "Erro interno do servidor"}, status_code=500)

def get_user_and_banco_from_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        print("[ERROR] Header Authorization ausente ou inválido")
        return None, None
    
    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        user_email = payload.get("email")
        user_role = payload.get("role")
        
        if not user_email or not user_role:
            print(f"[ERROR] Token não contém email ou role: {payload}")
            return None, None
        
        try:
            from util.mobile_utils import extrair_banco_do_token
            banco_usuario = extrair_banco_do_token(payload)
            
            if not banco_usuario:
                print(f"[ERROR] Não foi possível determinar banco_usuario para {user_email}")
                return None, None
                
            print(f"[INFO] Token válido para {user_email} (role: {user_role}, banco: {banco_usuario})")
            return payload, banco_usuario
            
        except Exception as import_error:
            print(f"[ERROR] Erro ao importar mobile_utils: {import_error}")
            import traceback
            traceback.print_exc()
            return None, None
        
    except jwt.JWTError as jwt_error:
        print(f"[ERROR] Erro JWT: {jwt_error}")
        return None, None
    except Exception as e:
        print(f"[ERROR] Erro ao extrair usuário e banco do token: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    import uvicorn
    print("[INFO] Iniciando servidor STOC...")
    print("[INFO] Acesse: http://localhost:8000")
    print("[INFO] Documentação da API: http://localhost:8000/docs")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
