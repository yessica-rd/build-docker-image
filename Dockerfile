# Usa una imagen base que incluya Python (por ejemplo, python:3.8)
FROM python:3.8

# Copia los archivos de tu proyecto al contenedor (asegúrate de tener un archivo de requerimientos)
COPY . /app

# Establece el directorio de trabajo
WORKDIR /app

# Instala las dependencias de tu proyecto (pytest en este caso)
RUN pip install -r requirements.txt

# Comando por defecto al ejecutar el contenedor
CMD ["pytest", "-v"]
