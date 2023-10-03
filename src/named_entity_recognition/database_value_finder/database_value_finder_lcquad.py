from named_entity_recognition.database_value_finder.database_value_finder import DatabaseValueFinder
from SPARQLWrapper import SPARQLWrapper, JSON


class DatabaseValueFinderSparql(DatabaseValueFinder):
    def __init__(self, database_name, db_schema_information, max_results=10):

        super().__init__(database_name, db_schema_information, max_results)

        """self.db_host = connection_config['database_host']
        self.db_port = connection_config['database_port']
        self.db_user = connection_config['database_user']
        self.db_password = connection_config['database_password']
        self.db_options = f"-c search_path={connection_config['database_schema']},cordis" """

        # as this thresholds are highly depending on the database specific implementation, it needs to be provided here
        self.exact_match_threshold = 1.0  # be aware that an exact match is not case sensitive
        self.high_similarity_threshold = 0.75
        self.medium_similarity_threshold = 0.5 #we changed this because .7 wasn't bringing up the most meaninful results in the KG literals index

    def find_similar_values_in_database(self,potential_values, include_primary_keys):
        matching_values = set()
        table_text_column_mapping = self._get_relevant_columns(include_primary_keys, text_columns_only=True)
        for table, columns in table_text_column_mapping.items():
            for column in columns:
                if column == '*':
                    matches = self._find_matches_in_column(table, column, potential_values)
                    if matches == None:
                        continue
                    matching_values.update(matches)

        # right now the similarity search on PostgreSQL supports only text columns due to the special indices

        return self._top_n_results(matching_values)

    def _find_matches_in_column(self, table, column, potential_values):
        query = self._assemble_query(table, column, potential_values)
        print(query)
        # toc = TicToc()
        # toc.tic()

        sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        sparql.setReturnFormat(JSON)

        sparql.setQuery(query)  # the previous query as a literal string

        results = sparql.query().convert()
        if results['boolean'] == True:
            #return list(map(lambda r: (potential_values[0], 1.0, column, table), results))
            return [(potential_values[0][0], 1.0, column, table)]
        """ cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        results= self._strip_uri(rows)"""

        #"NATural Language Energy for Promoting CONSUMER Sustainable Behaviour" 0.915493 0 0

        # r[0] is always the value of the column we query. r[1:] represents the similarity with all potential values.
        # Keep in mind that we only get the result back, if one of the similarities was higher than the similiarity-threshold
        # for this potential value. By using the max() function we therefore always get the similarity of the potential value
        # that matched best to the value of the column


        #return list(map(lambda r: (r[0], max(r[3:]), r[2], r[1]), results))

    def _strip_uri(self, rows):
        i=0
        while i < len(rows):
            rows[i] = list(rows[i])
            for idx, row in enumerate(rows[i]):
                if idx == 1 or idx == 2:
                    row = row.split('#')[-1]
                    row = row.rstrip('>')
                    rows[i][idx]=row
                    idx += 1
                else:
                    idx += 1
            i+=1
        return tuple(rows)

        # toc.toc(f"{table}.{column} took")
        #print(len(rows), rows)

    @staticmethod
    def _assemble_query(table,column, potential_values):
        """
        What we want to return in this method is a nested query looking like the following:
        select title, sim_v1, sim_v2, sim_v3 from
            (SELECT DISTINCT title,
                            similarity(title, 'Nural Language Energy for Promoting CONSUMER Sustainable Behaviour') as sim_v1,
                            similarity(title, 'dummy1')                                                             as sim_v2,
                            similarity(title, 'dummy2')                                                             as sim_v3
            FROM unics_cordis.projects
            WHERE title % 'Nural Language Energy for Promoting CONSUMER Sustainable Behaviour'
               OR title % 'dummy1'
               OR title % 'dummy2') as sub_query
        where sim_v1 >= 0.9 OR sim_v2 >= 0.5 OR sim_v2 >= 0.54

        Why is the nested query necessary? The special "gist_trgm_ops"-index we create for all text columns in the database works only with the % operator, not by using a WHERE similiarity(a,b) > x restriction. We therefore
        need the inner query to massively reduce the result set before applying the exact similarity restrictions in order to make this query fast.
        Be aware that the % operator works with the internal threshold set by set_limit(y) and returned by show_limit(). We therefore need to set the lowest possible threshold here (e.g. 0.499) and then use the other thresholds
        to further restrict the result set in the outer query.
        @return:

        SELECT lookupkey, originclass, originprop, sim_v0 FROM
            (SELECT DISTINCT
                    lookupkey,
                    originnameid,
                    similarity(lookupkey,'Framework Partnership Agreement') as sim_v0
            FROM soda_idx_metadata_values
            WHERE lookupkey % 'Framework Partnership Agreement') V
                JOIN
                    (SELECT originprop, originclass, id
                        FROM  soda_idx_metadata_origins) M
                    ON ( M.id = V.originnameid)
        WHERE sim_v0 >= 0.75


        """
        outer_query_selection = ', '.join([f'sim_v{i}' for i in range(0, len(potential_values))])
        outer_query_filter = ' OR '.join([f"sim_v{idx} >= {value[1]}" for idx, value in enumerate(potential_values)])
        inner_query_selection = ', '.join([f"similarity(literals,'{value[0]}') as sim_v{idx}" for idx, value in enumerate(potential_values)])
        #inner_query_filter = ' OR '.join([f" * % '{value[0]}'" for value in potential_values])
        #inner_query_filter = ','.join([f" * % '{value[0]}'" for value in potential_values])
        inner_query_filter = ', '.join([potential_values[0][0].replace(' ', '_')])
        # similarity_listening = reduce(lambda current, next_value: current + f" OR similarity({column},'{next_value[0]}') >= {next_value[1]}", potential_values, '')
        """full_query = f"SELECT literals, originclass, originprop, {outer_query_selection} FROM " \
                     f"(SELECT DISTINCT literals, originnameid, " \
                     f"{inner_query_selection} " \
                     f"FROM soda_idx_metadata_values " \
                     f"WHERE {inner_query_filter}) V " \
                     f"JOIN " \
                     f"(SELECT originprop, originclass, id " \
                     f"FROM  soda_idx_metadata_origins) M " \
                     f"ON ( M.id = V.originnameid) " \
                     f"WHERE {outer_query_filter} "
                     """
        full_query = f"ASK WHERE {{ <http://dbpedia.org/resource/{inner_query_filter}> a <http://dbpedia.org/ontology/{table.capitalize()}>}}"
        return full_query
        # print(full_query)
