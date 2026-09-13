class ReplaySemanticProvider:
    def __init__(self, recordings):
        self.recordings = dict(recordings)

    def interpret(self, request):
        return dict(self.recordings[request])
