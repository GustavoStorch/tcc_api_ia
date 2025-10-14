import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib
from app.models.base import SessionLocal 

def processar_e_treinar_modelo():
    
    db = SessionLocal()
    
    try:
        query = """
        SELECT
            a.situacao AS situacao_agendamento,
            a.horario_inicio,
            a.data_criacao,
            a.codpaciente
        FROM
            public.agendamentos a
        JOIN
            public.pacientes p ON a.codpaciente = p.codpaciente
        WHERE
            a.situacao IN ('Concluido', 'Nao Compareceu', 'Cancelado Pelo Paciente');
        """
        df = pd.read_sql(query, db.bind)
        print(f"Dados carregados do banco com sucesso: {len(df)} registos encontrados.")

        # Engenharia de Features
        df['horario_inicio'] = pd.to_datetime(df['horario_inicio'], errors='coerce', utc=True)
        df['data_criacao'] = pd.to_datetime(df['data_criacao'], errors='coerce', utc=True)

        df.dropna(subset=['horario_inicio', 'data_criacao'], inplace=True)

        df['no_show'] = df['situacao_agendamento'].apply(lambda x: 1 if x in ['Nao Compareceu', 'Cancelado Pelo Paciente'] else 0)
        
        # Realiza a normalização para meia noite e calcula a diferenã em dias.
        df['antecedencia_dias'] = (df['horario_inicio'].dt.normalize() - df['data_criacao'].dt.normalize()).dt.days
        df['dia_da_semana'] = df['horario_inicio'].dt.weekday
        df['mes'] = df['horario_inicio'].dt.month
        df['hora_do_dia'] = df['horario_inicio'].dt.hour
        
        df = df.sort_values(by='horario_inicio')
        df['historico_no_shows'] = df.groupby('codpaciente')['no_show'].cumsum() - df['no_show']
        df['historico_agendamentos'] = df.groupby('codpaciente').cumcount()
        df['taxa_no_show'] = (df['historico_no_shows'] / (df['historico_agendamentos'] + 1)).fillna(0)

        print("Engenharia de features concluída.")

        # Realiza a preparação dos Dados e do Treinamento
        
        features = [
            'antecedencia_dias', 'dia_da_semana', 'mes', 'hora_do_dia',
            'historico_no_shows', 'historico_agendamentos', 'taxa_no_show'
        ]
        target = 'no_show'
        
        df_model = df.dropna(subset=features + [target])

        if df_model.empty:
            print("ERRO: Nenhum dado válido restou para treinamento após a limpeza. Verifique os dados de origem.")
            return

        X = df_model[features]
        y = df_model[target]

        if len(X) < 2:
            print("ERRO: Dados insuficientes para dividir em treino e teste.")
            return

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        
        print("Treinando o modelo RandomForestClassifier...")
        model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        print("\n--- RELATÓRIO DE CLASSIFICAÇÃO (A PARTIR DO BANCO DE DADOS) ---")
        print(classification_report(y_test, y_pred, zero_division=0))
        print("-------------------------------------------------------")

        joblib.dump(model, 'no_show_model.pkl')
        joblib.dump(features, 'model_columns.pkl')
        
        print("\nProcesso de treinamento em background concluído com sucesso!")

    except Exception as e:
        print(f"ERRO no processo de treinamento em background: {e}")
    finally:
        db.close()

