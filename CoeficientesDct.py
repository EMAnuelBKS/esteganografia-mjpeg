import cv2
import numpy as np
import jpeglib

video = cv2.VideoCapture(
    'polyphia-ego-death-feat-steve-vai-official-music-video-ytmp4.savetube.vip.mp4'
)

if not video.isOpened():
    raise RuntimeError("Não foi possível abrir o vídeo.")

ret, frame = video.read()

if not ret:
    raise RuntimeError("Não foi possível extrair o frame.")

# Redimensiona para 380 x 280
frame = cv2.resize(frame, (380, 280))

# Salva um JPEG de teste com qualidade 90
cv2.imwrite(
    'frame_teste.jpg',
    frame,
    [cv2.IMWRITE_JPEG_QUALITY, 90]
)

video.release()

print("Frame salvo como frame_teste.jpg")

# Lê os coeficientes DCT do JPEG
jpeg = jpeglib.read_dct('frame_teste.jpg')

# Imprime as dimensões dos componentes
print("Y.shape:", jpeg.Y.shape)
print("Cb.shape:", jpeg.Cb.shape)
print("Cr.shape:", jpeg.Cr.shape)

# Imprime as tabelas de quantização
print("\nTabelas de quantização:")
print(jpeg.qt)

# Verifica o coeficiente DC de cada bloco Y
# jpeg.Y [bloco_vertical, bloco_horizontal, linha, coluna]
print("\nFormato dos coeficientes DC de Y:")
print(jpeg.Y[..., 0, 0].shape)

# Exibe os coeficientes DC dos primeiros blocos
print("\nCoeficientes DC de Y (primeiros blocos):")
print(jpeg.Y[:2, :2, 0, 0])

print("DC do primeiro bloco:", jpeg.Y[0, 0, 0, 0])

print("\nMatriz DCT do primeiro bloco:")
print(jpeg.Y[0, 0])

print("\nTodos os DC da componente Y:")
print(jpeg.Y[..., 0, 0])