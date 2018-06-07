from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from flask_socketio import SocketIO

from uuid import uuid4
from blockchain import blockchain


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


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    values = request.get_json()

    # Check that the required fields are in the POST'ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Create a new Transaction
    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
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



if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(port=port, host="0.0.0.0", debug=True)