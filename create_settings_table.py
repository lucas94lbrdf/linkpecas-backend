from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.models.setting import SystemSetting

def init_settings():
    # Cria a tabela se não existir
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Configurações iniciais
        initial_settings = [
            {"key": "google_analytics_id", "value": "", "description": "ID de acompanhamento do Google Analytics (ex: G-XXXXXXXXXX)"},
            {"key": "google_tag_manager_id", "value": "", "description": "ID do Google Tag Manager (ex: GTM-XXXXXXX)"},
            {"key": "google_search_console_id", "value": "", "description": "ID de verificação do Google Search Console"},
            {"key": "recaptcha_site_key", "value": "", "description": "Chave de Site (Pública) do Google reCAPTCHA v2"},
            {"key": "recaptcha_secret_key", "value": "", "description": "Chave Secreta do Google reCAPTCHA v2 (Criptografada)"},
            {"key": "ai_engine_selected", "value": "openai", "description": "Motor de IA principal (openai, gemini, claude)"},
            {"key": "openai_api_key", "value": "", "description": "API Key da OpenAI (Criptografada)"},
            {"key": "gemini_api_key", "value": "", "description": "API Key do Google Gemini (Criptografada)"},
            {"key": "claude_api_key", "value": "", "description": "API Key da Anthropic Claude (Criptografada)"},
        ]
        
        for setting_data in initial_settings:
            exists = db.query(SystemSetting).filter(SystemSetting.key == setting_data["key"]).first()
            if not exists:
                new_setting = SystemSetting(**setting_data)
                db.add(new_setting)
                print(f"Criando configuração: {setting_data['key']}")
        
        db.commit()
        print("Configurações inicializadas com sucesso!")
    except Exception as e:
        print(f"Erro ao inicializar configurações: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_settings()
