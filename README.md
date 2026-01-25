# Sistema de Control de Acceso Biométrico

Este proyecto es un sistema de control de acceso que utiliza un dispositivo biométrico para registrar la asistencia y controlar una puerta. Incluye una aplicación web para la gestión de usuarios y la visualización de registros.

## Características

-   **Autenticación de Usuarios:** Sistema de login para administradores y docentes.
-   **Gestión de Docentes:** Los administradores pueden crear, editar y eliminar docentes.
-   **Control de Puerta Remoto:** Los usuarios autenticados pueden abrir la puerta desde la aplicación web.
-   **Registro de Asistencia:** El sistema escucha los eventos del dispositivo biométrico y los guarda en una base de datos.
-   **Visualización de Registros:** Los administradores pueden ver todos los registros de acceso y los docentes pueden ver los suyos.
-   **Exportación de Reportes:** Los administradores pueden exportar los registros de asistencia a un archivo de Excel.
-   **Cambio de Contraseña:** Los usuarios pueden cambiar su propia contraseña.

## Estructura del Proyecto

-   `app.py`: Aplicación principal de Flask.
-   `biometrico_driver.py`: Driver para la comunicación con el dispositivo biométrico.
-   `sistema_tesis.db`: Base de datos SQLite donde se almacenan los datos.
-   `templates/`: Contiene las plantillas HTML para la interfaz web.
-   `requirements.txt`: Lista de las dependencias de Python.

## Configuración y Puesta en Marcha

1.  **Clonar el repositorio:**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd <NOMBRE_DEL_DIRECTORIO>
    ```

2.  **Crear un entorno virtual e instalar dependencias:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # En Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Configurar el dispositivo biométrico:**
    Asegúrate de que la dirección IP y las credenciales en `biometrico_driver.py` coincidan con la configuración de tu dispositivo.

4.  **Ejecutar la aplicación:**
    ```bash
    flask run
    ```
    La aplicación estará disponible en `http://127.0.0.1:5000`.

## Credenciales por Defecto

-   **Usuario:** admin
-   **Contraseña:** 1234
