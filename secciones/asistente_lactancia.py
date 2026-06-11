"""
asistente_lactancia.py
======================
Séptima sección del dashboard LactAnalytics.
Asistente de IA especializado en lactancia materna basado en
evidencia científica (OMS, AEPED, ABM, LLL).

Modelo: llama-3.3-70b-versatile (Groq) — gratuito
Seguridad: el system prompt bloquea respuestas fuera del ámbito
de lactancia y deriva siempre a profesionales sanitarios
para consultas médicas específicas.
"""

import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import os
from pathlib import Path

# Cargar variables de entorno
load_dotenv(Path(__file__).parents[1] / ".env")

# ---------------------------------------------------------------------------
# System prompt — blindado para seguridad sanitaria
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """
Eres LactBot, un asistente especializado en lactancia materna creado para
apoyar a madres, familias y profesionales sanitarios en España.

FUENTES EN LAS QUE BASAS TUS RESPUESTAS (exclusivamente):
- Guías de la OMS sobre lactancia materna (2023)
- Recomendaciones de la AEPED (Asociación Española de Pediatría)
- Protocolos de la ABM (Academy of Breastfeeding Medicine)
- Guías de La Leche League España (LLL)
- Evidencia científica publicada en revistas indexadas

REGLAS ESTRICTAS:
1. Solo respondes preguntas relacionadas con lactancia materna, alimentación
   infantil en el primer año, destete y apoyo emocional a madres lactantes.
2. Para cualquier pregunta sobre síntomas físicos, dolor intenso, fiebre,
   medicamentos o situaciones de urgencia, SIEMPRE derivas a:
   "Consulta con tu matrona, pediatra o asesora de lactancia certificada IBCLC."
3. NUNCA recomiendas marcas comerciales de leche de fórmula ni biberones.
4. NUNCA das dosis de medicamentos ni diagnósticos médicos.
5. Si la pregunta no es sobre lactancia, respondes:
   "Solo puedo ayudarte con dudas sobre lactancia materna.
   Para otras consultas, contacta con un profesional sanitario."
6. Siempre respondes en español, con un tono cálido, empático y sin tecnicismos.
7. Tus respuestas son concisas (máximo 150 palabras) salvo que se pida más detalle.
8. Al final de cada respuesta que implique una decisión importante añades:
   "💡 Recuerda: tu matrona o asesora IBCLC puede ayudarte personalmente."

DISCLAIMER PERMANENTE:
Este asistente ofrece información general basada en evidencia científica.
No sustituye la consulta con profesionales sanitarios.
"""

# ---------------------------------------------------------------------------
# Preguntas frecuentes sugeridas
# ---------------------------------------------------------------------------

PREGUNTAS_SUGERIDAS = [
    "¿Cada cuánto tiempo debe mamar un recién nacido?",
    "¿Cómo sé si mi bebé está tomando suficiente leche?",
    "¿Qué hago si tengo grietas en el pezón?",
    "¿Cuándo se establece la subida de leche?",
    "¿Puedo tomar ibuprofeno si estoy dando el pecho?",
    "¿Cómo conservo la leche materna extraída?",
    "¿Qué es la lactancia a demanda?",
    "¿Cómo introduzco el biberón sin abandonar el pecho?",
    "¿Hasta cuándo recomienda la OMS dar el pecho?",
    "¿Qué alimentos debo evitar durante la lactancia?",
]


# ---------------------------------------------------------------------------
# Helpers de UI
# ---------------------------------------------------------------------------

def _titulo_seccion(titulo: str, subtitulo: str = ""):
    st.html(f"""
    <div style="margin-bottom:1rem;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.4rem;
                    color:#1A2E35;line-height:1.2;">{titulo}</div>
        <div style="font-size:0.78rem;color:#648A96;margin-top:0.2rem;">
            {subtitulo}
        </div>
    </div>
    """)


def _mensaje_usuario(texto: str):
    st.html(f"""
    <div style="display:flex;justify-content:flex-end;margin-bottom:0.8rem;">
        <div style="background:#648A96;color:#F6F0E6;border-radius:14px 14px 4px 14px;
                    padding:0.7rem 1rem;max-width:75%;font-size:0.85rem;line-height:1.5;">
            {texto}
        </div>
    </div>
    """)


def _mensaje_bot(texto: str):
    st.html(f"""
    <div style="display:flex;justify-content:flex-start;margin-bottom:0.8rem;">
        <div style="background:#FFFFFF;color:#1A2E35;
                    border-radius:14px 14px 14px 4px;
                    padding:0.7rem 1rem;max-width:75%;font-size:0.85rem;
                    line-height:1.5;box-shadow:0 2px 8px rgba(100,138,150,0.10);">
            🤱 {texto}
        </div>
    </div>
    """)


# ---------------------------------------------------------------------------
# Llamada a la API de Groq
# ---------------------------------------------------------------------------

def _llamar_groq(historial: list) -> str:
    """
    Envía el historial de conversación a Groq y devuelve la respuesta.
    Maneja errores de API de forma elegante.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return (
            "⚠️ No se ha configurado la API key de Groq. "
            "Añade GROQ_API_KEY en el archivo .env del proyecto."
        )

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + historial,
            max_tokens=400,
            temperature=0.4,  # Bajo para respuestas más consistentes y seguras
        )
        return response.choices[0].message.content

    except Exception as e:
        error = str(e)
        if "rate_limit" in error.lower():
            return (
                "⏱️ Demasiadas consultas seguidas. Espera unos segundos e inténtalo de nuevo."
            )
        elif "invalid_api_key" in error.lower():
            return (
                "🔑 La API key no es válida. Comprueba el archivo .env."
            )
        else:
            return (
                f"❌ Error al conectar con el asistente. "
                f"Inténtalo de nuevo en unos momentos."
            )


# ---------------------------------------------------------------------------
# RENDER PRINCIPAL
# ---------------------------------------------------------------------------

def render():

    # Inicializar historial en session_state
    if "chat_historial" not in st.session_state:
        st.session_state.chat_historial = []

    # Cabecera
    st.html("""
    <div style="background:linear-gradient(135deg,#E8B8B8,#F6F0E6);
                border-radius:14px;padding:1.4rem 1.8rem;margin-bottom:1.5rem;
                border-left:4px solid #648A96;">
        <div style="font-family:'DM Serif Display',serif;font-size:1.3rem;
                    color:#1A2E35;line-height:1.4;">
            LactBot · Asistente de lactancia materna
        </div>
        <div style="font-size:0.8rem;color:#648A96;margin-top:0.4rem;">
            Respuestas basadas en evidencia científica · OMS · AEPED · ABM · LLL España<br>
            Este asistente no sustituye la consulta con tu matrona o pediatra.
        </div>
    </div>
    """)

    # Layout: chat a la izquierda, recursos a la derecha
    col_chat, col_recursos = st.columns([3, 1])

    with col_chat:

        # Historial de mensajes
        if not st.session_state.chat_historial:
            st.html("""
            <div style="background:#F6F0E6;border-radius:14px 14px 14px 4px;
                        padding:0.8rem 1rem;max-width:75%;font-size:0.85rem;
                        line-height:1.5;color:#1A2E35;margin-bottom:0.8rem;">
                🤱 Hola, soy LactBot. Estoy aquí para ayudarte con tus dudas
                sobre lactancia materna. Puedo orientarte sobre tomas,
                producción de leche, conservación, destete y mucho más.<br><br>
                ¿En qué puedo ayudarte hoy?
            </div>
            """)
        else:
            for msg in st.session_state.chat_historial:
                if msg["role"] == "user":
                    _mensaje_usuario(msg["content"])
                else:
                    _mensaje_bot(msg["content"])

        # Input del usuario
        with st.form("form_chat", clear_on_submit=True):
            col_input, col_btn = st.columns([5, 1])
            with col_input:
                pregunta = st.text_input(
                    "Tu pregunta",
                    placeholder="Escribe tu duda sobre lactancia...",
                    label_visibility="collapsed"
                )
            with col_btn:
                enviar = st.form_submit_button(
                    "Enviar",
                    use_container_width=True,
                    type="primary"
                )

        if enviar and pregunta.strip():
            # Añadir mensaje del usuario al historial
            st.session_state.chat_historial.append({
                "role": "user",
                "content": pregunta.strip()
            })

            # Obtener respuesta
            with st.spinner("LactBot está pensando..."):
                respuesta = _llamar_groq(st.session_state.chat_historial)

            # Añadir respuesta al historial
            st.session_state.chat_historial.append({
                "role": "assistant",
                "content": respuesta
            })

            st.rerun()

        # Botón limpiar conversación
        if st.session_state.chat_historial:
            if st.button("🗑️ Nueva conversación", use_container_width=False):
                st.session_state.chat_historial = []
                st.rerun()

    with col_recursos:

        _titulo_seccion("Preguntas frecuentes", "Pulsa para preguntar directamente")

        for pregunta_sug in PREGUNTAS_SUGERIDAS:
            if st.button(
                pregunta_sug,
                key=f"sug_{pregunta_sug[:20]}",
                use_container_width=True
            ):
                st.session_state.chat_historial.append({
                    "role": "user",
                    "content": pregunta_sug
                })
                with st.spinner("LactBot está pensando..."):
                    respuesta = _llamar_groq(st.session_state.chat_historial)
                st.session_state.chat_historial.append({
                    "role": "assistant",
                    "content": respuesta
                })
                st.rerun()

        st.markdown("---")

        st.html("""
        <div style="font-size:0.72rem;color:#648A96;line-height:1.7;">
            <strong style="color:#1A2E35;">Recursos oficiales:</strong><br>
            🔗 <a href="https://www.aeped.es/lactancia-materna"
                  style="color:#648A96;" target="_blank">AEPED · Lactancia</a><br>
            🔗 <a href="https://www.who.int/es/health-topics/breastfeeding"
                  style="color:#648A96;" target="_blank">OMS · Lactancia</a><br>
            🔗 <a href="https://lllespana.es"
                  style="color:#648A96;" target="_blank">LLL España</a><br>
            🔗 <a href="https://www.lactapp.es"
                  style="color:#648A96;" target="_blank">Lactapp</a><br><br>
            <strong style="color:#1A2E35;">¿Necesitas apoyo presencial?</strong><br>
            Busca una asesora certificada IBCLC en tu área en
            <a href="https://www.ilca.org/find-an-ibclc"
               style="color:#648A96;" target="_blank">ilca.org</a>
        </div>
        """)

        st.markdown("---")

        st.html("""
        <div style="background:#FFF0F0;border-radius:8px;
                    padding:0.7rem 0.9rem;font-size:0.7rem;
                    color:#C0392B;line-height:1.6;">
            <strong>⚠️ Aviso importante</strong><br>
            LactBot ofrece información general basada en evidencia científica.
            No sustituye la consulta médica personalizada. Ante cualquier
            síntoma o duda clínica, consulta siempre con tu matrona,
            pediatra o asesora IBCLC.
        </div>
        """)