# Organizador de Laboratório de Física

Aplicação web responsiva para organizar o acervo e os experimentos do Laboratório
de Física do Instituto Federal Catarinense (IFC), Campus Blumenau. O sistema
registra a localização de cada equipamento (bancada, porta e gaveta), cataloga
roteiros experimentais e permite que cada usuário crie pastas e salve favoritos.

No cadastro, o usuário escolhe o perfil. O domínio institucional precisa
corresponder à escolha: por padrão, `@ifc.edu.br` para docentes e
`@estudantes.ifc.edu.br` para discentes. Docentes podem cadastrar, consultar,
editar e excluir equipamentos e experimentos; discentes podem apenas consultá-los
e organizar seus próprios favoritos e pastas. Os domínios podem ser
personalizados por variáveis de ambiente.

## Requisitos

- Python 3.12 ou superior
- [uv](https://docs.astral.sh/uv/)

## Executar localmente

No terminal, na pasta do projeto:

```powershell
uv sync
uv run streamlit run src/teste_streamlit/app.py
```

O modo padrão é desenvolvimento e usa SQLite. O arquivo `laboratorio.db` é
criado na raiz do projeto na primeira execução. Também é possível iniciar com
`uv run teste-streamlit`.

Crie uma conta usando um e-mail de um dos domínios institucionais configurados e
entre com a senha escolhida. A recuperação de senha envia um código por e-mail;
configure SMTP conforme a seção abaixo para habilitá-la.

## Banco de dados

Em desenvolvimento, o sistema usa SQLite localmente. Para apontar para outro
banco durante o desenvolvimento, defina `DATABASE_URL`.

Em produção, defina `APP_ENV=production` e configure `MYSQL_DATABASE_URL` com
uma URL SQLAlchemy para MySQL, por exemplo:

```text
mysql+pymysql://usuario:senha@servidor:3306/nome_do_banco
```

No PowerShell:

```powershell
$env:APP_ENV = "production"
$env:MYSQL_DATABASE_URL = "mysql+pymysql://usuario:senha@servidor:3306/nome_do_banco"
uv run streamlit run src/teste_streamlit/app.py
```

Não versiona credenciais. No Streamlit Community Cloud, configure os parâmetros
em **App settings → Secrets**, usando o mesmo nome:

```toml
APP_ENV = "production"
MYSQL_DATABASE_URL = "mysql+pymysql://usuario:senha@servidor:3306/nome_do_banco"
```

O servidor MySQL precisa aceitar conexões do ambiente de hospedagem.

## E-mail e domínios institucionais

Para recuperação de senha, configure `SMTP_HOST`, `SMTP_PORT`,
`SMTP_FROM_EMAIL`, `SMTP_USERNAME` e `SMTP_PASSWORD`. `SMTP_USE_TLS` é opcional
e assume `true`. Esses valores também podem ser definidos nos secrets do
Streamlit Cloud.

Os domínios de perfil podem ser ajustados com listas separadas por vírgula:

- `TEACHER_EMAIL_DOMAINS` (padrão: `ifc.edu.br`)
- `STUDENT_EMAIL_DOMAINS` (padrão: `estudantes.ifc.edu.br`)

## Publicar no Streamlit Community Cloud

Publique o repositório no GitHub, crie um app em
[share.streamlit.io](https://share.streamlit.io/) e selecione
`src/teste_streamlit/app.py` como arquivo principal. Configure `APP_ENV`,
`MYSQL_DATABASE_URL` e as credenciais SMTP nos secrets do app antes de liberar o
acesso. Em produção, use um MySQL gerenciado e credenciais próprias para esse
serviço.
