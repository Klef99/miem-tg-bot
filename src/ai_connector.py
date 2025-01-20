from langchain_core.messages import HumanMessage
from langchain_gigachat.chat_models import GigaChat
from settings import settings
import json


class GigaChatConnector:
    def __init__(self):
        self.giga = GigaChat(
            credentials=settings.GIGACHAT_KEY,
            verify_ssl_certs=False,
            )

    def get_event_points(self, title: str, desc: str):
        ctx = f'Сгенерируй контрольные точки и их награду в баллах без лишних комментариев и в формате json {"title","reward_points"} для следующего мероприятия:\nНазвание мероприятия:\n {title}\nОписание мероприятия:\n{desc}\n'
        msg = HumanMessage(content=ctx)        
        res = self.giga.invoke([msg])
        return json.loads(res.content.replace("```json", "").replace("```", ""))

gigaChatConnector = GigaChatConnector()
