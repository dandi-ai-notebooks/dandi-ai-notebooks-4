import { useState, useEffect } from 'react';
import {
  ThemeProvider,
  createTheme,
  CssBaseline,
  Box,
  CircularProgress,
  Container,
  Typography
} from '@mui/material';
import { NotebookRecord, ReviewResults, ReviewResultType } from './types';
import NotebooksTable from './NotebooksTable';
import axios from 'axios';

const theme = createTheme({
  palette: {
    mode: 'light',
  },
});

function App() {
  const [notebooks, setNotebooks] = useState<NotebookRecord[]>([]);
  // const [critiques, setCritiques] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // const [notebookGradings, setNotebookGradings] = useState<NotebookGradingsData>([]);
  const [qualResults, setQualResults] = useState<Map<string, boolean>>(new Map());
  const [rankResults, setRankResults] = useState<Map<string, number>>(new Map());
  const [vetoResults, setVetoResults] = useState<Map<string, {user: string, reason: string}[]>>(new Map());

  useEffect(() => {
    loadData();
  }, []);

  // const modelForReviews = 'claude-3.7-sonnet';
  const modelForReviews = "gemini-2.5-pro-preview";

  const loadData = async () => {
    try {
      const reviewResultsResponse = await axios.get<ReviewResults>(
        'https://raw.githubusercontent.com/dandi-ai-notebooks/dandi-ai-notebooks-4/refs/heads/main/results.json'
      );
      const notebooks = reviewResultsResponse.data.results.filter(r => r.type === 'notebook');
      setNotebooks(notebooks);
      // setCritiques(new Set(critiquesResponse.data.files));
      // setNotebookGradings(gradingsResponse.data);

      const reviewResults = reviewResultsResponse.data.results.filter(r => (r.type !== "notebook"));
      const qualResults = new Map(
        reviewResults
          .filter((r): r is Extract<ReviewResultType, {type: 'qualification_test'}> => r.type === 'qualification_test')
          .map(r => [`${r.dandiset_id}/${r.version}/${r.subfolder}`, r.passing])
      );
      const rankResults = new Map(
        reviewResults
          .filter((r): r is Extract<ReviewResultType, {type: 'rankings'}> => r.type === 'rankings')
          .flatMap(r => r.notebooks.map((n, i) => [`${r.dandiset_id}/${r.version}/${n.subfolder}`, i + 1]))
      );
      setQualResults(qualResults);
      setRankResults(rankResults);

      const vetoResults = new Map(
        reviewResults
          .filter((r): r is Extract<ReviewResultType, {type: 'human_veto'}> => r.type === 'human_veto')
          .map(r => [`${r.dandiset_id}/${r.version}/${r.subfolder}`, r.vetoes])
      );
      setVetoResults(vetoResults);
    } catch (err) {
      setError('Failed to load data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
        <Typography color="error">{error}</Typography>
      </Box>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth={false}>
        <NotebooksTable
          notebooks={notebooks}
          // critiques={critiques}
          // notebookGradings={notebookGradings}
          qualResults={qualResults}
          rankResults={rankResults}
          modelForReviews={modelForReviews}
          vetoResults={vetoResults}
        />
      </Container>
    </ThemeProvider>
  );
}

export default App;
