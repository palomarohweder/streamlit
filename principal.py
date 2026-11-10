import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="OLAF - Organizador de Laboratório de Física",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicialização do Banco de Dados em Memória (Session State)
if "users" not in st.session_state:
    st.session_state.users = {
        "professor@ifc.edu.br": {
            "nome": "Carlos Professor",
            "senha": "12345678",
            "tipo": "Docente",
            "descricao": "Professor de Física do IFC Blumenau",
            "idioma": "Português"
        },
        "aluno@estudantes.ifc.edu.br": {
            "nome": "Maria Carvalho de Souza",
            "senha": "12345678",
            "tipo": "Discente",
            "descricao": "Eu sou incrível",
            "idioma": "Português"
        }
    }

if "logged_in_user" not in st.session_state:
    st.session_state.logged_in_user = None

if "equipamentos" not in st.session_state:
    st.session_state.equipamentos = [
        {
            "id": 1,
            "nome": "Microscópio",
            "quantidade": 3,
            "funcao": "Enxergar itens do tamanho micro",
            "porta": "2",
            "bancada": "3",
            "tags": "micro-organismo, microscopia, pequeno",
            "favorito": False,
            "imagem": "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=400"
        },
        {
            "id": 2,
            "nome": "Ebulidor",
            "quantidade": 2,
            "funcao": "Aquecer líquidos em experimentos termodinâmicos",
            "porta": "1",
            "bancada": "2",
            "tags": "calor, termodinâmica, ebulição",
            "favorito": False,
            "imagem": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=400"
        },
        {
            "id": 3,
            "nome": "Lentes",
            "quantidade": 10,
            "funcao": "Estudo da refração e ótica geométrica",
            "porta": "4",
            "bancada": "1",
            "tags": "ótica, luz, refração, lentes",
            "favorito": False,
            "imagem": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?w=400"
        }
    ]

if "experimentos" not in st.session_state:
    st.session_state.experimentos = [
        {
            "id": 1,
            "nome": "Gerador de Van de Graaff",
            "equipamentos": "Gerador de Van de Graaff, vareta mágica",
            "objetivos": "Estudar os processos de eletrização, compreender distribuição de cargas em condutores, demonstrar força de repulsão.",
            "resumo": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
            "tags": "Eletrostática, eletricidade, Gaiola de Faraday",
            "favorito": False,
            "imagem": "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=400"
        },
        {
            "id": 2,
            "nome": "Refração da luz",
            "equipamentos": "Lentes, Prisma, Laser",
            "objetivos": "Demonstrar a mudança de direção da luz ao passar de um meio para outro.",
            "resumo": "Experimento prático utilizando prismas para decomposição da luz branca em cores do arco-íris.",
            "tags": "ótica, luz, refração",
            "favorito": False,
            "imagem": "https://images.unsplash.com/photo-1507499739999-097706ad8914?w=400"
        }
    ]

if "pastas" not in st.session_state:
    st.session_state.pastas = {
        "Experimentos aula de eletrostática": ["Gerador de Van de Graaff"],
        "Aula de termodinâmica": ["Ebulidor"],
        "Experimentos divertidos": ["Refração da luz"]
    }

def validar_email_institucional(email):
    return email.endswith("@ifc.edu.br") or email.endswith("@estudantes.ifc.edu.br")

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main-header {
        font-size: 2.2rem;
        color: #0047AB;
        font-weight: bold;
    }
    .card {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        margin-bottom: 15px;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# Autenticação (Login / Cadastro / Recuperação)
if st.session_state.logged_in_user is None:
    st.markdown("<h1 style='text-align: center; color: #0047AB;'>⚡ OLAF - Organizador de Laboratório de Física</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Instituto Federal Catarinense - Campus Blumenau</p>", unsafe_allow_html=True)
    
    auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔑 Login", "📝 Cadastre-se", "❓ Esqueceu a senha?"])
    
    with auth_tab1:
        st.subheader("Bem-vindo ao OLAF! Entre com seu e-mail institucional.")
        login_email = st.text_input("E-mail institucional", placeholder="ex: nome@ifc.edu.br ou @estudantes.ifc.edu.br", key="log_email")
        login_senha = st.text_input("Senha", type="password", placeholder="Digite sua senha...", key="log_senha")
        
        if st.button("Entrar", type="primary"):
            if login_email in st.session_state.users and st.session_state.users[login_email]["senha"] == login_senha:
                st.session_state.logged_in_user = login_email
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos, ou usuário não cadastrado.")

    with auth_tab2:
        st.subheader("Cadastro de Novo Usuário")
        reg_nome = st.text_input("Nome de usuário", placeholder="Nome completo...", key="reg_nome_input")
        reg_email = st.text_input("Cadastre seu e-mail institucional", placeholder="seu.email@...ifc.edu.br", key="reg_email_input")
        reg_senha = st.text_input("Escolha uma senha", type="password", placeholder="Senha (exatamente 8 caracteres)...", key="reg_senha_input")
        reg_conf_senha = st.text_input("Confirme sua senha", type="password", placeholder="Confirme a senha...", key="reg_conf_senha_input")
        reg_tipo = st.radio("Selecione seu perfil:", ["Docente", "Discente"], horizontal=True, key="reg_tipo_input")
        
        if st.button("Finalizar Cadastro", type="primary"):
            if not validar_email_institucional(reg_email):
                st.error("Erro: O e-mail deve ser institucional (@ifc.edu.br ou @estudantes.ifc.edu.br).")
            elif len(reg_senha) != 8:
                st.error("A senha deve ter exatamente 8 caracteres.")
            elif reg_senha != reg_conf_senha:
                st.error("As senhas não coincidem.")
            elif reg_email in st.session_state.users:
                st.error("Este e-mail já está cadastrado.")
            else:
                st.session_state.users[reg_email] = {
                    "nome": reg_nome,
                    "senha": reg_senha,
                    "tipo": reg_tipo,
                    "descricao": "Membro do IFC Blumenau",
                    "idioma": "Português"
                }
                # Auto-login imediato após o cadastro
                st.session_state.logged_in_user = reg_email
                st.success("Cadastro realizado com sucesso! Entrando na página inicial...")
                st.rerun()

    with auth_tab3:
        st.subheader("Recuperação de Senha")
        rec_email = st.text_input("Informe seu e-mail institucional cadastrado:", key="rec_email_input")
        if st.button("Enviar Código de Verificação"):
            if validar_email_institucional(rec_email) and rec_email in st.session_state.users:
                st.info("Um código de verificação foi enviado para o seu e-mail institucional.")
                rec_codigo = st.text_input("Digite o código recebido:")
                nova_senha = st.text_input("Nova senha (8 caracteres):", type="password", key="nova_senha_input")
                if st.button("Redefinir Senha"):
                    if len(nova_senha) == 8:
                        st.session_state.users[rec_email]["senha"] = nova_senha
                        st.success("Senha alterada com sucesso!")
                    else:
                        st.error("A senha deve ter exatamente 8 caracteres.")
            else:
                st.error("E-mail institucional não encontrado no sistema.")

else:
    user_info = st.session_state.users[st.session_state.logged_in_user]
    
    # Menu lateral OLAF
    st.sidebar.markdown(f"### Olá, {user_info['nome']}")
    st.sidebar.markdown(f"**Perfil:** {user_info['tipo']}")
    st.sidebar.markdown(f"**Idioma:** {user_info.get('idioma', 'Português')}")
    st.sidebar.markdown("---")
    
    menu_opcao = st.sidebar.radio("Navegação OLAF", ["Início", "Equipamentos", "Experimentos", "Favoritos", "Pastas", "Perfil / Configurações"])
    
    if st.sidebar.button("Sair (Logout)"):
        st.session_state.logged_in_user = None
        st.rerun()

    # Início
    if menu_opcao == "Início":
        st.markdown("<h1 class='main-header'>BEM-VINDO AO OLAF</h1>", unsafe_allow_html=True)
        st.markdown("### Organização do Laboratório de Física - IFC Campus Blumenau")
        st.write("""
            O **OLAF** é uma aplicação desenvolvida para otimizar a gestão do laboratório de física, centralizando 
            a consulta e administração de equipamentos em bancadas e gavetas, além do registro de experimentos práticos.
        """)
        st.info(f"Você está logado como **{user_info['tipo']}**. Utilize o menu lateral para navegar entre Equipamentos, Experimentos, Favoritos e Pastas.")

    # Equipamentos
    elif menu_opcao == "Equipamentos":
        st.markdown("<h1 class='main-header'>EQUIPAMENTOS</h1>", unsafe_allow_html=True)
        termo_busca = st.text_input("🔍 Pesquisar equipamento por nome ou palavra-chave...", "")
        
        if user_info["tipo"] == "Docente":
            if st.button("➕ Cadastrar Novo Equipamento"):
                st.session_state.show_cad_eq = True
        
        if st.session_state.get("show_cad_eq", False) and user_info["tipo"] == "Docente":
            with st.form("form_cad_eq"):
                st.subheader("Cadastro de Equipamento")
                novo_nome = st.text_input("Nome do equipamento")
                nova_qtd = st.number_input("Quantidade", min_value=1, value=1)
                nova_func = st.text_input("Função do equipamento")
                nova_porta = st.text_input("Porta do equipamento (ex: 2)")
                nova_bancada = st.text_input("Bancada do equipamento (ex: 3)")
                novas_tags = st.text_input("Palavras-chave (separadas por vírgula)")
                nova_img = st.text_input("URL da Imagem", value="https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=400")
                
                submitted = st.form_submit_button("Salvar Equipamento")
                if submitted:
                    st.session_state.equipamentos.append({
                        "id": len(st.session_state.equipamentos) + 1,
                        "nome": novo_nome,
                        "quantidade": nova_qtd,
                        "funcao": nova_func,
                        "porta": nova_porta,
                        "bancada": nova_bancada,
                        "tags": novas_tags,
                        "favorito": False,
                        "imagem": nova_img
                    })
                    st.success("Equipamento cadastrado com sucesso!")
                    st.session_state.show_cad_eq = False
                    st.rerun()

        st.markdown("---")
        cols = st.columns(3)
        for idx, eq in enumerate(st.session_state.equipamentos):
            if termo_busca.lower() in eq["nome"].lower() or termo_busca.lower() in eq["tags"].lower():
                with cols[idx % 3]:
                    st.image(eq["imagem"], use_column_width=True)
                    st.markdown(f"""
                        <div class='card'>
                            <h3>{eq['nome']}</h3>
                            <p><b>Quantidade:</b> {eq['quantidade']} unidades</p>
                            <p><b>Função:</b> {eq['funcao']}</p>
                            <p>📍 <b>Localização:</b> Bancada {eq['bancada']}, Porta {eq['porta']}</p>
                            <p>🏷️ <b>Tags:</b> {eq['tags']}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    fav_label = "★ Favoritado" if eq["favorito"] else "☆ Favoritar"
                    if st.button(fav_label, key=f"fav_eq_{eq['id']}"):
                        eq["favorito"] = not eq["favorito"]
                        st.rerun()

    # Experimentos
    elif menu_opcao == "Experimentos":
        st.markdown("<h1 class='main-header'>EXPERIMENTOS</h1>", unsafe_allow_html=True)
        termo_exp = st.text_input("🔍 Pesquisar experimento...", "")
        
        if user_info["tipo"] == "Docente":
            if st.button("➕ Cadastrar Novo Experimento"):
                st.session_state.show_cad_exp = True
                
        if st.session_state.get("show_cad_exp", False) and user_info["tipo"] == "Docente":
            with st.form("form_cad_exp"):
                st.subheader("Cadastro de Experimento (Guia do Usuário)")
                exp_nome = st.text_input("Nome do experimento")
                exp_eqs = st.text_input("Equipamentos necessários")
                exp_obj = st.text_area("Objetivos do experimento")
                exp_res = st.text_area("Resumo / Tutorial (Texto ou link de vídeo)")
                exp_tags = st.text_input("Palavras-chave")
                exp_img = st.text_input("URL da Imagem", value="https://images.unsplash.com/photo-1507499739999-097706ad8914?w=400")
                
                if st.form_submit_button("Salvar Experimento"):
                    st.session_state.experimentos.append({
                        "id": len(st.session_state.experimentos) + 1,
                        "nome": exp_nome,
                        "equipamentos": exp_eqs,
                        "objetivos": exp_obj,
                        "resumo": exp_res,
                        "tags": exp_tags,
                        "favorito": False,
                        "imagem": exp_img
                    })
                    st.success("Experimento cadastrado com sucesso!")
                    st.session_state.show_cad_exp = False
                    st.rerun()
                    
        st.markdown("---")
        for exp in st.session_state.experimentos:
            if termo_exp.lower() in exp["nome"].lower() or termo_exp.lower() in exp["tags"].lower():
                with st.expander(f"🧪 {exp['nome']}"):
                    st.image(exp["imagem"], width=300)
                    st.write(f"**Equipamentos necessários:** {exp['equipamentos']}")
                    st.write(f"**Objetivo:** {exp['objetivos']}")
                    st.write(f"**Resumo / Tutorial:** {exp['resumo']}")
                    st.write(f"**Palavras-chave:** {exp['tags']}")
                    
                    fav_label = "★ Favorito" if exp["favorito"] else "☆ Favoritar"
                    if st.button(fav_label, key=f"fav_exp_{exp['id']}"):
                        exp["favorito"] = not exp["favorito"]
                        st.rerun()

    # Favoritos (com abertura de informações completas)
    elif menu_opcao == "Favoritos":
        st.markdown("<h1 class='main-header'>★ FAVORITOS</h1>", unsafe_allow_html=True)
        st.write("Aqui estão seus itens e experimentos salvos para acesso rápido. Clique para abrir as informações completas.")
        
        st.subheader("Equipamentos Favoritos")
        fav_eqs = [eq for eq in st.session_state.equipamentos if eq["favorito"]]
        if fav_eqs:
            for eq in fav_eqs:
                with st.expander(f"📌 {eq['nome']} (Bancada {eq['bancada']}, Porta {eq['porta']})"):
                    st.image(eq["imagem"], width=250)
                    st.write(f"**Quantidade:** {eq['quantidade']} unidades")
                    st.write(f"**Função:** {eq['funcao']}")
                    st.write(f"**Localização:** Bancada {eq['bancada']}, Porta {eq['porta']}")
                    st.write(f"**Palavras-chave:** {eq['tags']}")
        else:
            st.write("Nenhum equipamento favoritado.")
            
        st.subheader("Experimentos Favoritos")
        fav_exps = [exp for exp in st.session_state.experimentos if exp["favorito"]]
        if fav_exps:
            for exp in fav_exps:
                with st.expander(f"🧪 {exp['nome']}"):
                    st.image(exp["imagem"], width=250)
                    st.write(f"**Equipamentos necessários:** {exp['equipamentos']}")
                    st.write(f"**Objetivo:** {exp['objetivos']}")
                    st.write(f"**Resumo / Tutorial:** {exp['resumo']}")
                    st.write(f"**Palavras-chave:** {exp['tags']}")
        else:
            st.write("Nenhum experimento favoritado.")

    # Pastas (com criação e adição de itens)
    elif menu_opcao == "Pastas":
        st.markdown("<h1 class='main-header'>📁 Pastas de Organização</h1>", unsafe_allow_html=True)
        
        with st.form("form_criar_pasta"):
            st.subheader("Criar Nova Pasta e Adicionar Itens")
            nova_pasta_nome = st.text_input("Nome da pasta temática:")
            
            todos_itens = [eq["nome"] for eq in st.session_state.equipamentos] + [exp["nome"] for exp in st.session_state.experimentos]
            itens_selecionados = st.multiselect("Selecione os itens para adicionar à pasta:", todos_itens)
            
            if st.form_submit_button("Criar Pasta"):
                if nova_pasta_nome and nova_pasta_nome not in st.session_state.pastas:
                    st.session_state.pastas[nova_pasta_nome] = itens_selecionados
                    st.success(f"Pasta '{nova_pasta_nome}' criada com sucesso!")
                    st.rerun()
                elif nova_pasta_nome in st.session_state.pastas:
                    st.error("Já existe uma pasta com esse nome.")
                else:
                    st.error("Digite um nome válido para a pasta.")
                
        st.markdown("---")
        st.subheader("Suas Pastas")
        for nome_pasta, itens in st.session_state.pastas.items():
            with st.expander(f"📁 {nome_pasta} ({len(itens)} itens)"):
                if itens:
                    for item in itens:
                        st.markdown(f"- {item}")
                else:
                    st.write("Nenhum item adicionado nesta pasta.")
                
                novo_item_extra = st.selectbox(f"Adicionar item em '{nome_pasta}':", ["Selecione..."] + [i for i in todos_itens if i not in itens], key=f"sel_{nome_pasta}")
                if st.button(f"Adicionar à {nome_pasta}", key=f"btn_add_{nome_pasta}"):
                    if novo_item_extra != "Selecione...":
                        st.session_state.pastas[nome_pasta].append(novo_item_extra)
                        st.success(f"Item '{novo_item_extra}' adicionado com sucesso!")
                        st.rerun()

    # Perfil / Configurações (com salvamento correto do idioma)
    elif menu_opcao == "Perfil / Configurações":
        st.markdown("<h1 class='main-header'>⚙️ Configurações da Conta</h1>", unsafe_allow_html=True)
        
        with st.form("form_perfil"):
            edit_nome = st.text_input("Editar nome de usuário", value=user_info["nome"])
            edit_email = st.text_input("E-mail institucional", value=st.session_state.logged_in_user, disabled=True)
            edit_senha = st.text_input("Editar senha (8 caracteres)", value=user_info["senha"], type="password")
            
            idioma_atual = user_info.get("idioma", "Português")
            idx_idioma = 0 if idioma_atual == "Português" else 1
            edit_idioma = st.selectbox("Idioma", ["Português", "English"], index=idx_idioma)
            
            edit_desc = st.text_input("Descrição da conta", value=user_info.get("descricao", ""))
            
            if st.form_submit_button("SALVAR ALTERAÇÕES"):
                if len(edit_senha) != 8:
                    st.error("A senha deve ter exatamente 8 caracteres.")
                else:
                    user_info["nome"] = edit_nome
                    user_info["senha"] = edit_senha
                    user_info["idioma"] = edit_idioma
                    user_info["descricao"] = edit_desc
                    st.success("Alterações salvas com sucesso!")
                    st.rerun()