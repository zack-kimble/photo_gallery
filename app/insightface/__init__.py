import torch

def model_loader():
    checkpoint = 'app/insightface/BEST_checkpoint_r101.tar'
    checkpoint = torch.load(checkpoint)
    model = checkpoint['model'].module
    return model