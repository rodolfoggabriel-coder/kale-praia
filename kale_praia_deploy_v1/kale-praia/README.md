# 🏖️ KALE PRAIA — Painel Admin

Sistema de Reservas KALE PRAIA — Painel Administrativo v1.

## Deploy no Render (passo a passo)

### 1. Criar repositório no GitHub
```bash
git init
git add .
git commit -m "KALE PRAIA Painel v1"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/kale-praia-painel.git
git push -u origin main
```

### 2. Criar Web Service no Render
1. Acesse https://render.com e faça login
2. Clique em **"New +"** → **"Web Service"**
3. Conecte seu repositório GitHub
4. Configure:
   - **Name:** `kale-praia-painel`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --bind 0.0.0.0:$PORT`
5. Clique em **"Create Web Service"**
6. Aguarde ~2 minutos — URL gerada automaticamente!

### URL ficará no formato:
`https://kale-praia-painel.onrender.com`

## Estrutura
```
kale-praia/
├── app.py              # Flask server com detecção de dispositivo
├── requirements.txt    
├── render.yaml         # Config automática do Render
└── templates/
    └── index.html      # Painel completo (mobile + desktop)
```

## Detecção de Dispositivo
O servidor detecta automaticamente se o usuário está em:
- **mobile** → Bottom nav + FAB + layout otimizado
- **tablet** → Layout intermediário  
- **desktop** → Sidebar fixa + layout completo

## Contatos
- Desenvolvimento: Rodolfo
- Administração KALE: Erika — +55 61 99123-4203
- Instagram: @kalepraia
