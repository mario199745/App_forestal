# Aplicación de evaluación forestal

Tablero Streamlit para explorar producción por árbol, morfología de vainas y
semillas, y resultados de taninos.

## Fuentes

El aplicativo utiliza exclusivamente los libros:

- `Data_ProduccionArbol_FINAL.xlsx`
- `Data_MorfotipoMedidas_FINAL.xlsx`
- `Data_TaninosVainas_FINAL.xlsx`

## Ejecución con Conda

Desde la raíz del proyecto:

```powershell
conda activate sigexpert
python App_forestal/etl/build_database.py
streamlit run App_forestal/app.py
```

La base ya generada se encuentra en `App_forestal/data/forestal.db`. Solo es
necesario reconstruirla cuando cambien los Excel o las reglas del ETL.

## Pruebas

```powershell
python -m unittest discover -s App_forestal/tests -v
```

## Estructura

```text
App_forestal/
├── .streamlit/config.toml
├── app.py
├── database.py
├── data/forestal.db
├── etl/build_database.py
├── scripts/profile_data.py
├── tests/test_app.py
└── requirements.txt
```

La conexión a SQLite es de solo lectura. Las consultas y la conexión están
cacheadas por Streamlit. Los filtros vacíos representan todos los valores.
