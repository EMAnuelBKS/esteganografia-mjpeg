import cv2
import jpeglib
import tempfile
import os

cap = cv2.VideoCapture(
    'polyphia-ego-death-feat-steve-vai-official-music-video-ytmp4.savetube.vip.mp4'
)

if not cap.isOpened():
    print("Erro: Não foi possível encontrar ou abrir o vídeo original.")
    exit()


# Arquivo temporário para gerar cada JPEG
with tempfile.TemporaryDirectory() as temp_dir:

    caminho_jpeg = os.path.join(temp_dir, 'frame.jpg')

    with open('filme.mjpeg', 'wb') as f:

        contador = 0

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            # Redimensiona o frame
            frame = cv2.resize(frame, (380, 280))

            # OpenCV utiliza BGR; jpeglib espera RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Converte o array de pixels para um objeto JPEG
            imagem = jpeglib.from_spatial(frame_rgb)

            # Comprime e salva como JPEG.  qt =  qualidade da comrpessão
            imagem.write_spatial(caminho_jpeg, qt=90)

            # Lê os bytes do JPEG gerado
            with open(caminho_jpeg, 'rb') as jpeg_file:
                jpeg = jpeg_file.read()

            # Calcula o tamanho em bytes
            tamanho = len(jpeg)

            
            contador += 1
            if( ( tamanho / 1024 ) > 65 ):
                print(f"Frame {contador}: {tamanho} bytes ultrapassou o limite de 65 KB ({tamanho / 1024:.2f} KB)")

            # O cabeçalho possui exatamente 5 bytes
            if tamanho > 99999:
                raise ValueError(
                    f"JPEG do frame {contador} excedeu o limite de 5 dígitos."
                )

            tamanho_cabecalho = str(tamanho).zfill(5)

            # Escreve o cabeçalho e os dados binários
            f.write(tamanho_cabecalho.encode('utf-8'))
            f.write(jpeg)

cap.release()

print("Conversão concluída!")
print("Vídeo possui {contador} frames ")
