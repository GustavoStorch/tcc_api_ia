from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

class LembreteService:
    def get_lembretes_pendentes(self, db: Session) -> List[dict]:
        # A query busca agendamentos com risco 'Alto' ou 'Médio' que ainda não foram confirmados.
        query = text("""
            SELECT
                p.nome as nome_paciente,
                p.telegram_chat_id,
                pr.nome as nome_profissional,
                a.horario_inicio,
                (a.horario_inicio::date - CURRENT_DATE) as dias_restantes
            FROM agendamentos a
            JOIN pacientes p ON a.codpaciente = p.codpaciente
            JOIN profissionais pr ON a.codprofissional = pr.codprofissional
            WHERE
                a.risco IN ('Alto', 'Médio') AND
                a.situacao = 'Agendado' AND
                p.telegram_chat_id IS NOT NULL AND
                (a.horario_inicio::date - CURRENT_DATE IN (1, 3));
        """)

        result = db.execute(query).mappings().all()
        return [dict(row) for row in result]

lembrete_service = LembreteService()