from datetime import datetime
import json
import requests

from app.utils.azure_utils import get_azure_header


def send_system_teams_alert(application, exception, user):

    title = 'NOTIFICAÇÃO DE APLICAÇÃO EM ERRO'
    # Monta o Adaptive Card
    message_data = {
        "body": {
            "contentType": "html",
            "content": f'<p><span style="font-size: 20px;">🚨</span><b><strong class="editor-text-bold" style="font-size: 20px;"> </strong></b><b><strong class="editor-text-bold" style="font-size: 20px;">{title}</strong></b></p><attachment id="card"></attachment>'
        },
        "attachments": [
            {
                "id": "card",
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": json.dumps({
                    "type": "AdaptiveCard",
                    "version": "1.5",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "body": [
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": "Aplicação:",
                                            "wrap": True,
                                            "weight": "Bolder"
                                        }
                                    ],
                                    "horizontalAlignment": "Left"
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "horizontalAlignment": "Right",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "wrap": True,
                                            "id": "Application",
                                            "text": str(application)
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": "Usuário:",
                                            "wrap": True,
                                            "weight": "Bolder"
                                        }
                                    ],
                                    "horizontalAlignment": "Left"
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "horizontalAlignment": "Right",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "wrap": True,
                                            "id": "User",
                                            "text": str(user)
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": "Horário:",
                                            "wrap": True,
                                            "weight": "Bolder"
                                        }
                                    ],
                                    "horizontalAlignment": "Left"
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "horizontalAlignment": "Right",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "wrap": True,
                                            "id": "Datetime",
                                            "text": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                                        }
                                    ]
                                }
                            ]
                        },
                        {
                            "type": "ColumnSet",
                            "columns": [
                                {
                                    "type": "Column",
                                    "width": "auto",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "text": "Erro:",
                                            "wrap": True,
                                            "weight": "Bolder"
                                        }
                                    ],
                                    "horizontalAlignment": "Left"
                                },
                                {
                                    "type": "Column",
                                    "width": "stretch",
                                    "horizontalAlignment": "Right",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "wrap": True,
                                            "id": "Error",
                                            "text": str(exception)
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                })
            }
        ]
    }
    '''
    send_teams_message( # Cassiano
        user_id="0b203b27-a7a4-4541-8e7f-ec38cf909729"
        , message=message_data
    )


    send_teams_message( # Dyevelenn
        user_id="ef08d13b-563d-4d31-b297-c366ae304848"
        , message=message_data
    )

    send_teams_message( # Vanderson
        user_id="eaed6edd-c423-4ce4-8fd7-cf5087ee3ebd"
        , message=message_data
    )
    
    '''


def send_teams_message(user_id, message):
    """
    Envia um Adaptive Card para um usuário específico via chat privado no Teams.
    user_id: id do usuário destino (AAD)
    title: título da mensagem
    card: dict do Adaptive Card
    """
    # Cria o chat one-on-one (se não existir)
    chat_data = {
        "chatType": "oneOnOne",
        "members": [
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": "https://graph.microsoft.com/v1.0/users('0db5aea7-7afd-436a-bd83-a1b057b683da')"
            },
            {
                "@odata.type": "#microsoft.graph.aadUserConversationMember",
                "roles": ["owner"],
                "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')"
            }
        ]
    }
    chat_url = "https://graph.microsoft.com/v1.0/chats"
    chat_response = requests.post(chat_url, json=chat_data, headers=get_azure_header(), verify=False)
    chat_id = chat_response.json().get("id")    
    
    message_url = f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages"
    message_response = requests.post(message_url, json=message, headers=get_azure_header(), verify=False)
    
    if message_response.status_code != 201:
        print("Erro ao enviar mensagem Teams:", message_response.json(), flush=True)
