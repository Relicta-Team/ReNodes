

import json


class CodeGenerator:
    def __init__(self):
        self.generated_code = ""
        self.graphsys = None

    def getNodeLibData(self,cls):
        return self.graphsys.nodeFactory.getNodeLibData(cls)

    def generate_graph_code(self, graph_data):
        nodes = graph_data.get('nodes', {})
        for node_id, node_data in nodes.items():
            obj = self.getNodeLibData(node_data['class_'])
            print(f"node {obj['name']}: {obj['path']}")

        #connections = graph_data.get('connections', [])
        #for connection in connections:
        #    connection_code = self.generate_connection_code(connection)
        #    self.generated_code += f"{connection_code}\n"
    def generate_from_serialized_data(self, graph_data):
        self.generate_graph_code(graph_data)
        #print(self.generated_code)

    def generateProcess(self):
        file_path = "./session.json"
        try:
            with open(file_path) as data_file:
                layout_data = json.load(data_file)
        except Exception as e:
            layout_data = None
            print('Cannot read data from file.\n{}'.format(e))

        if not layout_data:
            return

        self.generate_from_serialized_data(layout_data)