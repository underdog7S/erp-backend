import os
from openai import OpenAI
from api.models.communications import CommunicationThread, CommunicationMessage
from api.models.tenant_features import TenantFeatureConfig

# Initialize client globally but allow fallback for Django checks
api_key = os.getenv("OPENAI_API_KEY", "dummy_key_for_builds")
client = OpenAI(api_key=api_key)

def generate_smart_reply(thread: CommunicationThread, max_tokens: int = 150) -> str:
    """
    Reads the last 10 messages of a thread and generates an AI response.
    Context is injected based on the Tenant's industry and settings.
    """
    # Grab the tenant's configuration
    tenant = thread.tenant
    
    # 1. Build the System Prompt
    system_prompt = f"You are a helpful, professional assistant for a business named '{tenant.name}'."
    if tenant.industry:
        system_prompt += f" This business operates in the {tenant.industry} industry."
    
    system_prompt += (
        " Keep your answers concise, friendly, and helpful. "
        "Do not make up fake prices or fake booking links. If you don't know, politely say so."
    )
    
    messages_payload = [{"role": "system", "content": system_prompt}]
    
    # 2. Grab chat history (last 10 messages)
    history = CommunicationMessage.objects.filter(thread=thread).order_by('-created_at')[:10]
    # Reverse to get chronological order
    history = list(history)[::-1]
    
    for msg in history:
        role = "user" if msg.sender_type == 'client' else "assistant"
        messages_payload.append({"role": role, "content": msg.content})
        
    # 3. Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Highly cost-effective model for VAR SaaS
            messages=messages_payload,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        reply_text = response.choices[0].message.content
        
        # 4. Save tokens used for billing
        config = TenantFeatureConfig.objects.filter(tenant=tenant).first()
        if config and hasattr(response, 'usage'):
            tokens_used = response.usage.total_tokens
            config.ai_tokens_used_this_month += tokens_used
            config.save(update_fields=['ai_tokens_used_this_month'])
            
        return reply_text
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return "I'm sorry, I'm having trouble processing that right now. Please try again later."
