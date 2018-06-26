from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO

from uuid import uuid4
from blockchain import blockchain

from reg_var import Register, Sign, Verify, User

# Instantiate the Node
app = Flask(__name__)
cors = CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    proof, mined_hash = blockchain.proof_of_work(last_block)

    socketio.emit('lose_mine', {"lose": True}, broadcast=True)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender=node_identifier,
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, mined_hash, previous_hash, node_identifier)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

@app.route('/transfer', methods=['POST'])
def transfer():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['recipient', 'amount', 'wallet_address']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # check recipient is valid
    recipient = User(values['recipient'])
    recipient_addr = recipient.verify()

    if not recipient_addr:
        return jsonify({'error': True, 'errMsg': 'Account not exist'}), 401

    # check sender's saving
    addr_trans, saving = blockchain.find_wallet(values['wallet_address'])
    if saving < values['amount']:
        return jsonify({'error': True, 'errMsg': 'Not enough money.'})


    # generate new transaction
    transaction = {
        'sender': values['wallet_address'],
        'recipient': recipient_addr,
        'amount': values['amount']
    }

    # sign the transaction
    sign = Sign(values['wallet_address'], transaction)
    cipher = sign.sign()

    # if can't sign the transaction
    if not cipher:
        return jsonify({'error': True, 'errMsg': 'Cannot sign transaction'}), 401

    # verify the signature
    verify = Verify(values['wallet_address'], transaction, cipher)
    result = verify.verify()

    # verify failed
    if not result:
        return jsonify({'error': True, 'errMsg': 'Signature Verify Fail'}), 401

    # verify successfully
    index = blockchain.new_transaction(values['wallet_address'], recipient_addr, values['amount'])
    response = {'message': f'Transaction will be added to Block {index}'}

    # broadcast new transaction to all miners online
    socketio.emit('new_transaction', 'new transaction', broadcast=True)

    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


@app.route('/client_mine', methods=['GET'])
def client_mine():
    last_block = blockchain.last_block
    last_hash = blockchain.hash(last_block)
    last_proof = last_block['proof']

    response = {
        'last_hash': last_hash,
        'last_proof': last_proof
    }

    return jsonify(response), 200

@app.route('/block_verify', methods=['POST'])
def block_verify():
    data = request.get_json()

    print(data)

    proof = data['proof']
    mined_hash = data['hash']
    miner = data['miner']

    previous_hash = blockchain.hash(blockchain.last_block)

    if mined_hash[:4] == "0000":
        blockchain.new_transaction(sender=node_identifier, recipient=miner, amount=5)
        new_block = blockchain.new_block(proof, mined_hash, previous_hash, miner)

        socketio.emit('lose_mine', {"lose": True}, broadcast=True)

        response = {
            "verify": True,
            "award": 5,
            "new_block": new_block
        }
    else:
        response = {
            "verify": False
        }

    return jsonify(response), 200

@app.route('/new_wallet', methods=['POST'])
def new_wallet():
    value = request.get_json()
    pid = value['data']

    if pid is None:
        return "Error: Please supply a valid list of nodes", 400
    else:
        register = Register(pid)
        register.new_wallet()

        response = {
            'public_key':register.wallet_address,
            'private_key':register.private_key,
            'message':'Please save your key carefully.'
        }
        return jsonify(response), 200

@app.route('/login', methods=['POST'])
def login():
    value = request.get_json()

    if 'pid' not in value:
        return 'Missing values', 400

    user = User(value['pid'])
    result = user.verify()

    if result:
        response = {
            'login': True,
            'wallet_address': result
        }

        return jsonify(response), 200

    response = {
        'login': False
    }

    return jsonify(response), 401


@app.route('/transactions/sign', methods=['POST'])
def sign():
    values = request.get_json()

    required = ['pid', 'transaction']

    if not all(k in values for k in required):
        return 'Missing values', 400

    sign = Sign(values['pid'],values['transaction'])
    cipher = sign.sign()

    if cipher:
        response = {
            'cipher':sign.sign()
        }

        return jsonify(response), 200
    else:
        return 401



@app.route('/transactions/verify', methods=['POST'])
def verify():
    values = request.get_json()

    required = ['wallet_address','transaction','cipher']
    if not all(k in values for k in required):
        return 'Missing values', 400

    verify = Verify(values['wallet_address'],values['transaction'],values['cipher'])

    response = {
        'result':verify.verify()
    }
    return jsonify(response), 200


@app.route('/wallet/transactions', methods=['POST'])
def search_address():
    values = request.get_json()

    address = values.get('address')
    if address is None:
        return "Error: Please supply a valid address", 400

    addr_trans, saving = blockchain.find_wallet(address)

    response = {
        'address': address,
        'result': addr_trans,
        'saving': saving
    }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(port=port, host="0.0.0.0", debug=True)
