from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

# Setup Flask
app = Flask(__name__)
api = Api(app)

# Setup MongoDB database
client = MongoClient("mongodb://db:27017")
db = client.SimilarityDB
users = db["Users"]


def UserExist(username):
    """
    Check whether a username is already registered.

    Params
    ____________
    username: str

    Returns
    ____________
    True, False: Boolean
    """
    if users.find({"Username":username}).count() == 0:
        return False
    else:
        return True

class Register(Resource):
    """
    Creates a POST request which allows user to
    register to API service with a username, 
    password, and is provided with a default of
    6 tokens for purchase.

    Params
    ____________
    Resource: class
    
    Returns
    ____________
    retJson: JSON object

    """
    def post(self):
        #Step 1 is to get posted data by the user
        postedData = request.get_json(force=True)

        #Get the data
        username = postedData["username"]
        password = postedData["password"] #"123xyz"

        if UserExist(username):
            retJson = {
                'status':301,
                'msg': 'Invalid Username'
            }
            return jsonify(retJson)

        hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

        #Store username and pw into the database
        users.insert({
            "Username": username,
            "Password": hashed_pw,
            "Tokens":6
        })

        retJson = {
            "status": 200,
            "msg": "You successfully signed up for the API"
        }
        return jsonify(retJson)

def verifyPw(username, password):
    """
    Verifies whether user entered correct password
    matching to the appropriate hashed password in 
    the MongoDB document (record).

    Params
    ____________
    username: str
    password: str

    Returns
    ____________
    True, False: Boolean

    """
    if not UserExist(username):
        return False

    hashed_pw = users.find({
        "Username":username
    })[0]["Password"]

    if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
        return True
    else:
        return False

def countTokens(username):
    """
    Counts number of tokens held by the
    user.

    Params
    ____________
    username: str
        
    Returns
    ____________
    tokens: int
    """
    tokens = users.find({
        "Username":username
    })[0]["Tokens"]
    return tokens

class Detect(Resource):
    """
    Detects similarity between two sentences
    of text
    """
    def post(self):
        #Step 1 get the posted data
        postedData = request.get_json(force=True)

        #Step 2 is to read the data
        username = postedData["username"]
        password = postedData["password"]
        text1 = postedData["text1"]
        text2 = postedData["text2"]

        if not UserExist(username):
            retJson = {
                'status':301,
                'msg': "Invalid Username"
            }
            return jsonify(retJson)
        #Step 3 verify the username pw match
        correct_pw = verifyPw(username, password)

        if not correct_pw:
            retJson = {
                "status":302,
                "msg": "Incorrect Password"
            }
            return jsonify(retJson)
        #Step 4 Verify user has enough tokens
        num_tokens = countTokens(username)
        if num_tokens <= 0:
            retJson = {
                "status": 303,
                "msg": "You are out of tokens, please refill!"
            }
            return jsonify(retJson)

        #Calculate edit distance between text1, text2
        import spacy
        nlp = spacy.load('en_core_web_sm')
        text1 = nlp(text1)
        text2 = nlp(text2)

        ratio = text1.similarity(text2)

        retJson = {
            "status":200,
            "ratio": ratio,
            "msg":"Similarity score calculated successfully"
        }

        #Take away 1 token from user
        current_tokens = countTokens(username)
        users.update({
            "Username":username
        }, {
            "$set":{
                "Tokens":current_tokens-1
                }
        })

        return jsonify(retJson)

class Refill(Resource):
    """
    Allows admin to refill number of tokens
    held by the user if depleted.
    """
    def post(self):
        postedData = request.get_json(force=True)

        username = postedData["username"]
        password = postedData["admin_pw"]
        refill_amount = postedData["refill"]

        if not UserExist(username):
            retJson = {
                "status": 301,
                "msg": "Invalid Username"
            }
            return jsonify(retJson)

        correct_pw = "abc123"
        if not password == correct_pw:
            retJson = {
                "status":304,
                "msg": "Invalid Admin Password"
            }
            return jsonify(retJson)

        #MAKE THE USER PAY!
        users.update({
            "Username":username
        }, {
            "$set":{
                "Tokens":refill_amount
                }
        })

        retJson = {
            "status":200,
            "msg": "Refilled successfully"
        }
        return jsonify(retJson)


api.add_resource(Register, '/register')
api.add_resource(Detect, '/detect')
api.add_resource(Refill, '/refill')


if __name__=="__main__":
    app.run(host='0.0.0.0')
