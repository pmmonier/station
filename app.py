#! /usr/bin/env python
import sys
import time
import os
basePath = os.path.abspath(os.getcwd())
greengrass_device_path = basePath + '/greengrass_device'
sys.path.append(greengrass_device_path)
from flask import Flask
from flask_restful import Api, Resource, reqparse
from flask_cors import CORS, cross_origin
from greengrass_device import iotDevice
device = iotDevice()
app = Flask(__name__)
api = Api(app)
CORS(app, resources={r"/*": {"origins": "*"}})
app.config['CORS_HEADERS'] = 'Content-Type'

class Station(Resource):
        @app.route('/validate-playslip',methods=['GET', 'POST'])
        def validate():
                print('hereeeeeee',basePath)
                parser = reqparse.RequestParser()
                parser.add_argument("playSlipBarcode")
                parser.add_argument("stationNumber")
                params = parser.parse_args()
                params['method'] = 'validatePlaySlipBarcode'
                print(params)
                return device.publishMessage(params)

        @app.route('/match-playslip-ticket',methods=['GET', 'POST'])
        def match():
                parser = reqparse.RequestParser()
                parser.add_argument("playSlipBarcode")
                parser.add_argument("ticketBarcode")
                parser.add_argument("stationNumber")
                params = parser.parse_args()
                params['method'] = 'marryPlaySlipTicket'
                return device.publishMessage(params)

        @app.route('/fix-playslip',methods=['GET', 'POST'])
        def fix():
                parser = reqparse.RequestParser()
                parser.add_argument("playSlipBarcode")
                parser.add_argument("stationNumber")
                params = parser.parse_args()
                params['method'] = 'fixPlaySlip'
                return device.publishMessage(params)

api.add_resource(Station,"/validate-playslip", "/match-playslip-ticket", "/fix-playslip")

if __name__ == '__main__':
        from waitress import serve
        serve(app, host="localhost", port=5000)
        # app.run(debug=True)



