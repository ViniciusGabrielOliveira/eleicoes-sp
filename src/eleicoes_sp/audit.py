"""Confere cada categoria de votos com a totalização independente por seção."""
from .query import rows

def reconcile(con):
    return rows(con,"""WITH calculated AS (
      SELECT year,election,round,municipality,zone,section,office,
        coalesce(sum(votes) FILTER(WHERE vote_kind='nominal'),0)::BIGINT AS nominal_votes,
        coalesce(sum(votes) FILTER(WHERE vote_kind='blank'),0)::BIGINT AS blank_votes,
        coalesce(sum(votes) FILTER(WHERE vote_kind='null'),0)::BIGINT AS null_votes,
        coalesce(sum(votes) FILTER(WHERE vote_kind='party'),0)::BIGINT AS party_votes,
        coalesce(sum(votes) FILTER(WHERE vote_kind='annulled'),0)::BIGINT AS annulled_votes
      FROM votes GROUP BY ALL)
      SELECT coalesce(c.office,t.office) AS office,coalesce(c.round,t.round) AS round,
        count(*) AS sections,
        count(*) FILTER(WHERE t.office IS NULL) AS missing_official_sections,
        count(*) FILTER(WHERE coalesce(c.nominal_votes,0)<>coalesce(t.nominal_votes,0)
          OR coalesce(c.blank_votes,0)<>coalesce(t.blank_votes,0)
          OR coalesce(c.null_votes,0)<>coalesce(t.null_votes,0)
          OR coalesce(c.party_votes,0)<>coalesce(t.party_votes,0)
          OR coalesce(c.annulled_votes,0)<>coalesce(t.annulled_votes,0)) AS mismatched_sections
      FROM calculated c FULL OUTER JOIN turnout t
        USING(year,election,round,municipality,zone,section,office)
      GROUP BY ALL ORDER BY office,round""")
