# alpacaCloudMcpServer

steps to run this on cloud :

Create an app service
Make sure to copy the keys for .env file from "C:\mcpCnfig\mcpServerList.json"
In the azure app service :
Add the environemnt variables 
most importantly add PORT 8000

The most important is the startup command
pip install -r requirements.txt && python -m src.alpaca_mcp_server.server --transport http --host 0.0.0.0 --port ${PORT}

And then also remmber when yo uupload the zip file
Everything should be inside the root of the zip