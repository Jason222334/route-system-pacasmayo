# Sistema Optimizador de Rutas de Entrega (VRPTW) 🚚📍

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)
![n8n](https://img.shields.io/badge/Workflow-n8n-orange)
![PostgreSQL](https://img.shields.io/badge/Database-PostGIS-336791)
![Docker](https://img.shields.io/badge/Container-Docker-blue)

## 📄 Descripción

Este proyecto presenta el diseño e implementación de un sistema integrado para la optimización de rutas de distribución de última milla. El sistema resuelve variantes del **Problema de Enrutamiento de Vehículos con Ventanas de Tiempo (VRPTW)** utilizando algoritmos heurísticos y metaheurísticos.

La solución combina la automatización de flujos de trabajo mediante **n8n** con una interfaz interactiva desarrollada en **Streamlit**, permitiendo:
* Procesamiento de datos en tiempo real.
* Generación automática de rutas óptimas.
* Visualización dinámica de resultados en mapas.

## 🚀 Características Principales

* **Arquitectura Modular:** Integración de servicios mediante contenedores Docker.
* **Restricciones Operativas:** Soporte para capacidad vehicular, ventanas de tiempo y múltiples depósitos.
* **Interfaz Interactiva:** Visualización geoespacial clara para la toma de decisiones ágil.
* **Optimización:** Reducción significativa de costos operativos y tiempos de planificación.

## 🛠️ Stack Tecnológico

El desarrollo se basó en las siguientes herramientas y librerías:

| Componente | Herramienta / Librería |
|------------|------------------------|
| **Lenguaje** | Python 3.11.x |
| **Frontend** | Streamlit 1.24.x |
| **Orquestación** | n8n |
| **Base de Datos** | PostgreSQL 14 + PostGIS 3.x |
| **Mapas/Ruteo** | OpenRouteService / Mapbox |
| **Algoritmos** | OR-Tools, NetworkX, Pandas, Geopandas |
| **Infraestructura** | Docker |

## 📊 Arquitectura del Sistema

El flujo de datos sigue la siguiente estructura:
1.  **Ingesta:** Carga de datos automatizada vía n8n.
2.  **Procesamiento:** Cálculo de matrices de distancia y optimización (Python/OR-Tools).
3.  **Almacenamiento:** Gestión de datos espaciales en PostGIS.
4.  **Visualización:** Presentación de rutas y KPIs en Streamlit.

## 💾 Instalación y Uso

### Prerrequisitos
* Docker y Docker Compose
* Python 3.11+
* API Keys para OpenRouteService o Mapbox

### Pasos
1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/tu-usuario/nombre-del-repo.git](https://github.com/tu-usuario/nombre-del-repo.git)
    cd nombre-del-repo
    ```

2.  **Configurar variables de entorno:**
    Crea un archivo `.env` basado en el ejemplo proporcionado e ingresa tus credenciales de base de datos y API Keys.

3.  **Ejecutar con Docker:**
    ```bash
    docker-compose up --build
    ```

4.  **Ejecución Manual (Solo Streamlit):**
    ```bash
    pip install -r requirements.txt
    streamlit run app.py
    ```

## 📈 Resultados e Impacto

Según las pruebas experimentales realizadas en un entorno logístico real:
* ✅ **Reducción del 18.3%** en distancias totales recorridas.
* ✅ **Reducción del 24.7%** en tiempos de computación vs. métodos tradicionales.
* ✅ **Mejora en Usabilidad:** Nivel de satisfacción del usuario de 4.36/5.

## 👥 Autores

* **Winny Lizbeth Amambal Vásquez**
* **Jason Anderson Gálvez Luna**
* **André Jhonel Rodríguez Preciado**

---
*Facultad de Ingeniería, Ingeniería de Sistemas - Universidad Nacional de Trujillo*
