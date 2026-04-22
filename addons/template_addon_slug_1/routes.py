from fastapi import FastAPI
from fastapi import Request
from fastapi.templating import Jinja2Templates
def main(app: FastAPI, templates: Jinja2Templates, config_loader):
    @app.get("/config_template")
    @app.post("/config_template")
    def config_template():
        return "This is a template route for the configuration GUI of addons. You can replace this with your own HTML and logic to create a custom configuration page for your addon."