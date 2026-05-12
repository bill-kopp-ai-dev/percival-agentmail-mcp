import asyncio
from percival_agentmail_mcp.client import AgentMailClientWrapper
from percival_agentmail_mcp.config import load_config

async def main():
    config = load_config()
    wrapper = AgentMailClientWrapper(config.api_key)
    try:
        res = await wrapper.client.inboxes.messages.send(
            inbox_id=config.inbox_id,
            to=["bill.kopp.dev@gmail.com"],
            subject="Test",
            text="Testing"
        )
        print("Success:", res)
    except Exception as e:
        print("Error type:", type(e))
        print("Error:", str(e))

asyncio.run(main())
