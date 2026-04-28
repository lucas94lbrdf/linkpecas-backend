import os
import requests

RESEND_API_KEY = "re_huFrKpeN_A5XXJ9gc4Pq2VkLUU8Bouufi"

# Se você ainda não validou um domínio próprio no Resend (ex: contato@linkpeca.com.br), 
# use o e-mail padrão "onboarding@resend.dev" para testes (ele só envia para o seu próprio e-mail).
SENDER_EMAIL = "onboarding@resend.dev" 

def send_email(to_email: str, subject: str, html_content: str):
    try:
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "from": f"Auto Marketplace <{SENDER_EMAIL}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content
        }
        response = requests.post("https://api.resend.com/emails", headers=headers, json=data)
        response_data = response.json()
        
        if response.status_code in [200, 201]:
            return {"status": "success", "id": response_data.get("id")}
        else:
            print(f"Erro ao enviar e-mail: {response_data}")
            return {"status": "error", "message": response_data}
    except Exception as e:
        print(f"Erro ao enviar e-mail (exceção): {e}")
        return {"status": "error", "message": str(e)}

# --- TEMPLATES ---

def send_welcome_email(to_email: str, name: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-w-xl mx-auto; color: #333; padding: 20px;">
        <h1 style="color: #ff6b35;">Bem-vindo ao LinkPeça, {name}! 🚗</h1>
        <p>Sua conta foi criada com sucesso.</p>
        <p>Estamos muito felizes em ter você na maior comunidade de peças e acessórios automotivos. Agora você pode cadastrar seus produtos, avaliar lojas e participar das nossas comunidades.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="http://localhost:5173/login" style="background-color: #ff6b35; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold;">Acessar minha conta</a>
        </div>
        <p>Se tiver qualquer dúvida, basta responder este e-mail.</p>
        <p style="color: #888; font-size: 12px; margin-top: 40px;">Equipe LinkPeça</p>
    </div>
    """
    return send_email(to_email, "Bem-vindo ao LinkPeça! 🎉", html)

def send_password_recovery(to_email: str, name: str, reset_link: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-w-xl mx-auto; color: #333; padding: 20px;">
        <h2 style="color: #ff6b35;">Recuperação de Senha</h2>
        <p>Olá, {name},</p>
        <p>Recebemos um pedido para redefinir a senha da sua conta no LinkPeça.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_link}" style="background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold;">Redefinir Minha Senha</a>
        </div>
        <p>Se você não solicitou essa mudança, por favor ignore este e-mail. O link expira em 1 hora.</p>
        <p style="color: #888; font-size: 12px; margin-top: 40px;">Equipe LinkPeça</p>
    </div>
    """
    return send_email(to_email, "Recuperação de Senha - LinkPeça", html)

def send_product_created(to_email: str, name: str, product_title: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-w-xl mx-auto; color: #333; padding: 20px;">
        <h2 style="color: #10b981;">Produto Cadastrado! ✅</h2>
        <p>Olá, {name},</p>
        <p>O seu anúncio <strong>"{product_title}"</strong> foi recebido com sucesso no nosso sistema.</p>
        <p>Se o seu plano permite aprovação automática, ele já está no ar. Caso contrário, ele entrou na fila de análise da nossa moderação.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="http://localhost:5173/my-links" style="background-color: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold;">Ver Meus Anúncios</a>
        </div>
        <p style="color: #888; font-size: 12px; margin-top: 40px;">Equipe LinkPeça</p>
    </div>
    """
    return send_email(to_email, "Produto Cadastrado com Sucesso - LinkPeça", html)

def send_product_pending(to_email: str, name: str, product_title: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-w-xl mx-auto; color: #333; padding: 20px;">
        <h2 style="color: #f59e0b;">Anúncio em Análise ⏳</h2>
        <p>Olá, {name},</p>
        <p>O seu anúncio <strong>"{product_title}"</strong> está aguardando a aprovação da nossa equipe.</p>
        <p>Como padrão para manter a qualidade do marketplace, nossa equipe analisa novos links para evitar spans e links falsos. Avisaremos assim que ele for liberado!</p>
        <p>Para aprovação automática imediata em todos os seus links, considere atualizar para o Plano Pro.</p>
        <p style="color: #888; font-size: 12px; margin-top: 40px;">Equipe LinkPeça</p>
    </div>
    """
    return send_email(to_email, "Seu anúncio está em análise - LinkPeça", html)

def send_product_expired(to_email: str, name: str, product_title: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-w-xl mx-auto; color: #333; padding: 20px;">
        <h2 style="color: #ec4899;">Link Expirado ⏰</h2>
        <p>Olá, {name},</p>
        <p>Notamos que a validade da oferta para o produto <strong>"{product_title}"</strong> expirou.</p>
        <p>Ele não está mais visível para os compradores. Acesse seu painel para atualizar a validade, alterar o preço ou inativar permanentemente o produto.</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="http://localhost:5173/my-links" style="background-color: #ec4899; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold;">Atualizar Meu Anúncio</a>
        </div>
        <p style="color: #888; font-size: 12px; margin-top: 40px;">Equipe LinkPeça</p>
    </div>
    """
    return send_email(to_email, "Sua oferta expirou - LinkPeça", html)

def send_account_blocked(to_email: str, name: str, reason: str):
    html = f"""
    <div style="font-family: Arial, sans-serif; max-w-xl mx-auto; color: #333; padding: 20px; border: 2px solid #ef4444; border-radius: 8px;">
        <h2 style="color: #ef4444; text-align: center;">Conta Bloqueada 🚫</h2>
        <p>Olá, {name},</p>
        <p>Sua conta no LinkPeça foi suspensa devido a uma infração de nossos Termos de Uso.</p>
        <p><strong>Motivo:</strong> {reason}</p>
        <p>Seus anúncios foram temporariamente inativados. Se você acredita que isso foi um engano, por favor, entre em contato com nosso suporte respondendo este e-mail.</p>
        <p style="color: #888; font-size: 12px; margin-top: 40px;">Suporte LinkPeça</p>
    </div>
    """
    return send_email(to_email, "Sua conta foi suspensa - LinkPeça", html)
