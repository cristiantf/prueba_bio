# Sistema de Control de Acceso Biométrico con Flask

Este proyecto implementa un sistema de control de acceso y asistencia utilizando un dispositivo biométrico Hikvision, una placa NodeMCU para el control de una cerradura eléctrica, y una aplicación web desarrollada con Flask para la gestión y monitoreo.

## Características Principales

-   **Autenticación de Usuarios:** Sistema de login seguro con roles (administrador, docente).
-   **Gestión de Docentes:** El administrador puede crear, editar, eliminar y asignar permisos a los docentes.
-   **Control de Puerta Remoto:** Apertura de la puerta desde la aplicación web, con permisos asignables.
-   **Registro de Asistencia en Tiempo Real:** Un servicio en segundo plano escucha constantemente los eventos del biométrico (asistencias, intentos fallidos) y los registra en la base de datos.
-   **Dashboard de Administrador:** Visualización de los últimos eventos en tiempo real, gestión de docentes y generación de reportes.
-   **Dashboard de Docente:** Visualización de los registros de asistencia propios y opción para apertura de puerta (si tiene permiso).
-   **Exportación de Reportes:** Generación de reportes de asistencia en formato Excel (`.xlsx`) con un formato matricial por fechas.
-   **Gestión de Perfil:** Los usuarios pueden cambiar su propia contraseña de forma segura.

## Estructura del Proyecto

```
prueba_bio/
│
├── app.py                  # Aplicación principal de Flask (rutas, lógica de negocio)
├── biometrico_driver.py    # Driver para la comunicación con el biométrico y NodeMCU
├── config.py               # Archivo de configuración centralizado (IPs, claves)
├── requirements.txt        # Dependencias de Python
├── sistema_tesis.db        # Base de datos SQLite
├── node.ino                # Código para la placa NodeMCU (control de la puerta)
├── templates/              # Plantillas HTML para la interfaz web
│   ├── admin.html
│   ├── docente.html
│   ├── login.html
│   └── ...
└── ...
```

## Componentes de Hardware

1.  **Dispositivo Biométrico:** Un terminal Hikvision (u otro compatible con el protocolo ISAPI).
2.  **NodeMCU (ESP8266):** Microcontrolador para recibir la orden de apertura desde la aplicación web y accionar un relé.
3.  **Módulo de Relé:** Para controlar la cerradura eléctrica.
4.  **Cerradura Eléctrica:** El dispositivo final para asegurar la puerta.

## Configuración y Puesta en Marcha

Siga estos pasos para configurar y ejecutar el proyecto en su entorno local.

### 1. Prerrequisitos

-   Python 3.8 o superior.
-   Dispositivo biométrico y NodeMCU configurados en la misma red local.

### 2. Clonar el Repositorio

```bash
git clone <URL_DEL_REPOSITORIO>
cd prueba_bio
```

### 3. Entorno Virtual y Dependencias

Es altamente recomendable utilizar un entorno virtual.

```bash
# Crear un entorno virtual
python -m venv .venv

# Activar el entorno virtual
# En Windows:
.venv\Scripts\activate
# En macOS/Linux:
# source .venv/bin/activate

# Instalar las dependencias
pip install -r requirements.txt
```

### 4. Configuración de Red

Edite el archivo `config.py` con las direcciones IP y credenciales correctas:

```python
# config.py

# ...
IP_BIO = '192.168.1.22'      # IP de tu dispositivo biométrico
USER_BIO = 'admin'           # Usuario del biométrico
PASS_BIO = 'istae1804A'      # Contraseña del biométrico

IP_NODE = 'puerta-tesis.local' # IP o hostname de tu NodeMCU
TOKEN_NODE = 'istae1805A'    # Token de seguridad (debe coincidir en node.ino)
# ...
```

### 5. Inicializar y Ejecutar la Aplicación

Al ejecutar la aplicación por primera vez, la base de datos se creará automáticamente.

```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`.

## Credenciales por Defecto

Al iniciar la aplicación por primera vez, se crea un usuario administrador con las siguientes credenciales:

-   **Usuario:** `admin`
-   **Contraseña:** `istae123A*`

**Nota:** Se recomienda cambiar esta contraseña después del primer inicio de sesión.

## Generar el Instalador `.exe`

Para crear un archivo ejecutable autocontenido para Windows, se utiliza `pyinstaller`.

1.  **Asegurarse de tener PyInstaller:**
    ```bash
    pip install pyinstaller
    ```

2.  **Generar el ejecutable:**
    Desde la raíz del proyecto, ejecute el siguiente comando:
    ```bash
    pyinstaller --onefile --windowed --name "SistemaTesis" --add-data "templates;templates" --add-data "sistema_tesis.db;." app.py
    ```
    -   `--onefile`: Crea un único archivo `.exe`.
    -   `--windowed`: Evita que se abra una consola al ejecutar la aplicación.
    -   `--name "SistemaTesis"`: Nombre del archivo ejecutable.
    -   `--add-data "templates;templates"`: Incluye la carpeta de plantillas HTML en el paquete.
    -   `--add-data "sistema_tesis.db;."`: Incluye la base de datos.

    El archivo `SistemaTesis.exe` se encontrará en la carpeta `dist`.