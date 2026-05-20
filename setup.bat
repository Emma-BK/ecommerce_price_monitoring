@echo off
echo ==========================================================
echo     🚀 INSTALLATION DE L'ENVIRONNEMENT (WINDOWS) 🚀
echo ==========================================================

echo [1/4] Recherche de Python...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Python n'est pas reconnu. Assurez-vous d'avoir installe Python 3 et de l'avoir ajoute au PATH.
    pause
    exit /b
)

echo [2/4] Creation du Virtual Environment (venv)...
python -m venv venv
call venv\Scripts\activate.bat

echo [3/4] Mise a jour de pip et installation des dependances...
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [4/4] Initialisation Terminee !
echo ==========================================================
echo L'environnement est prêt !
echo Pour lancer une premiere synchronisation et modele XGBoost :
echo python ecommerce_price_prediction.py
echo.
echo Pour lancer l'API FastAPI :
echo python -m uvicorn api_predictions:app --reload
echo.
echo Appuyez sur une touche pour quitter ce script. L'environnement venv est desormais configure.
pause
