# Aplicacion de evaluacion forestal

Tablero Streamlit para explorar informacion Tara e INIA. Tara se presenta en
una sola pestaña denominada `Proyecto Tara Ñan`. La version vigente ya no
consume la fuente de taninos y no incluye la pestana Comparacion.

## Fuentes

El aplicativo utiliza:

- `DATA/Tara/Data_InformacionSitios_FINAL.xlsx`
- `DATA/Tara/Data_ClimaSitios_FINAL.xlsx`
- `DATA/Tara/Data_SuelosSitios_FINAL.xlsx`
- `DATA/INIA/informacion_extraida_INIA_SERFOR.md`

## Ejecucion con Conda

Desde la raiz del proyecto:

```powershell
& 'C:\Users\USUARIO\miniconda3\Scripts\conda.exe' run -n sigexpert python scripts/prepare_tara_inia_data.py
& 'C:\Users\USUARIO\miniconda3\Scripts\conda.exe' run -n sigexpert streamlit run App_forestal/app.py
```

La base generada se encuentra en `App_forestal/data/forestal.db`. Solo es
necesario reconstruirla cuando cambien los Excel, el Markdown INIA o las reglas
del ETL.

## Pruebas

```powershell
& 'C:\Users\USUARIO\miniconda3\Scripts\conda.exe' run -n sigexpert python -m unittest discover -s App_forestal/tests -v
```

## Estructura

```text
App_forestal/
├── app.py
├── database.py
├── data/forestal.db
├── etl/build_database.py
├── tests/test_app.py
└── requirements.txt

scripts/
└── prepare_tara_inia_data.py
```

La conexion a SQLite es de solo lectura. Las consultas y la conexion estan
cacheadas por Streamlit. Los filtros vacios representan todos los valores.
