import torch

def model_loader(device):
    checkpoint = 'app/insightface/BEST_checkpoint_r101.tar'
    if torch.cuda.is_available():
        checkpoint = torch.load(checkpoint)
    else:
        checkpoint = torch.load(checkpoint, map_location=device)
    model = checkpoint['model'].module
    return model