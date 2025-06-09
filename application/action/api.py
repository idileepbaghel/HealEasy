from flask import Blueprint
from flask_restful import Api, Resource, reqparse, abort

tasks = {
    1: {
        "task": "Hey all!!!",
        "message": "How are you guys...."
    },
    2: {
        "task": "generate api",
        "message": "generate a string"
    },
    3: {
        "task": "create api",
        "message": "shot it"
    }
}

task_post_args = reqparse.RequestParser()
task_post_args.add_argument("task", type=str, help="task is required", required=True)
task_post_args.add_argument("message", type=str, help="task is message", required=True)

class hello(Resource):
    def get(self):
        return tasks

class task(Resource):
    def get(self, task_id):
        return tasks[task_id]
    
    def post(self, task_id):
        args = task_post_args.parse_args()
        if task_id in tasks:
            abort(409, "task_id already exists")
        tasks[task_id] = {"task": args["task"], "message": args["message"]}
        return tasks[task_id]

# Create a Blueprint
api_bp = Blueprint('api', __name__)
api = Api(api_bp)

# Add the HelloWorld resource to the API
api.add_resource(task, '/tasks/<int:task_id>')
api.add_resource(hello, '/tasks')