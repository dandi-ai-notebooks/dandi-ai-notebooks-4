import { useMemo, useState } from 'react';
import { Metadata, NotebookRecord } from './types';
import { Button } from '@mui/material';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  Select,
  MenuItem,
  InputLabel,
  TableSortLabel,
  Typography,
  Link,
  Tooltip
} from '@mui/material';

type SortKey = keyof Metadata | 'est_cost' | 'qual' | 'rank' | 'vetoes';

type SortConfig = {
  key: SortKey;
  direction: 'asc' | 'desc';
};

interface Props {
  notebooks: NotebookRecord[];
  // critiques: Set<string>;
  // notebookGradings: NotebookGradingsData;
  qualResults: Map<string, boolean>;
  rankResults: Map<string, number>;
  modelForReviews: string;
  vetoResults: Map<string, {user: string, reason: string}[]>;
}

export default function NotebooksTable({ notebooks, qualResults, rankResults, modelForReviews, vetoResults }: Props) {
  const [selectedDandiset, setSelectedDandiset] = useState<string>('');
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    key: 'timestamp' as SortKey,
    direction: 'desc'
  });

  const uniqueDandisets = useMemo(() => {
    const dandisets = [...new Set(notebooks.map(n => n.dandiset_id))];
    return dandisets.sort();
  }, [notebooks]);

  const handleSort = (key: SortKey) => {
    const direction = sortConfig.key === key && sortConfig.direction === 'asc' ? 'desc' : 'asc';
    setSortConfig({ key, direction });
  };

  const getPromptUrl = (prompt: string) => {
    return `https://github.com/dandi-ai-notebooks/dandi-ai-notebooks-4/blob/main/scripts/templates/generate_notebook/${prompt}.txt`;
  };

  const bestNonVetoedNotebooks = useMemo(() => {
    const bestByDandiset = new Map<string, string>(); // dandiset_id -> notebook key

    // Group notebooks by dandiset
    const byDandiset = new Map<string, NotebookRecord[]>();
    notebooks.forEach(notebook => {
      const current = byDandiset.get(notebook.dandiset_id) || [];
      current.push(notebook);
      byDandiset.set(notebook.dandiset_id, current);
    });

    // Find best non-vetoed notebook for each dandiset
    byDandiset.forEach((dandisetNotebooks, dandisetId) => {
      let bestRank = Number.MAX_SAFE_INTEGER;
      let bestKey = '';

      dandisetNotebooks.forEach(notebook => {
        const key = `${notebook.dandiset_id}/${notebook.version}/${notebook.subfolder}`;
        const rank = rankResults.get(key) ?? Number.MAX_SAFE_INTEGER;
        const isVetoed = vetoResults.has(key);

        if (!isVetoed && rank < bestRank) {
          bestRank = rank;
          bestKey = key;
        }
      });

      if (bestKey) {
        bestByDandiset.set(dandisetId, bestKey);
      }
    });

    return bestByDandiset;
  }, [notebooks, rankResults, vetoResults]);

  const filteredAndSortedNotebooks = useMemo(() => {
    const filtered = selectedDandiset
      ? notebooks.filter(n => n.dandiset_id === selectedDandiset)
      : notebooks;


    return [...filtered].sort((a, b) => {
      if (sortConfig.key === 'qual') {
        const aQual = qualResults.get(`${a.dandiset_id}/${a.version}/${a.subfolder}`) ?? false;
        const bQual = qualResults.get(`${b.dandiset_id}/${b.version}/${b.subfolder}`) ?? false;
        return sortConfig.direction === 'asc'
          ? (aQual === bQual ? 0 : aQual ? 1 : -1)
          : (aQual === bQual ? 0 : aQual ? -1 : 1);
      }

      if (sortConfig.key === 'rank') {
        const aRank = rankResults.get(`${a.dandiset_id}/${a.version}/${a.subfolder}`) ?? Number.MAX_SAFE_INTEGER;
        const bRank = rankResults.get(`${b.dandiset_id}/${b.version}/${b.subfolder}`) ?? Number.MAX_SAFE_INTEGER;
        return sortConfig.direction === 'asc'
          ? aRank - bRank
          : bRank - aRank;
      }

      if (sortConfig.key === 'vetoes') {
        const aVetoes = vetoResults.get(`${a.dandiset_id}/${a.version}/${a.subfolder}`)?.length ?? 0;
        const bVetoes = vetoResults.get(`${b.dandiset_id}/${b.version}/${b.subfolder}`)?.length ?? 0;
        return sortConfig.direction === 'asc'
          ? aVetoes - bVetoes
          : bVetoes - aVetoes;
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let aValue: string | number = (a as any)[sortConfig.key] || '';
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let bValue: string | number = (b as any)[sortConfig.key] || '';

      if (sortConfig.key === 'model') {
        aValue = a.model.split('/')[1] || '';
        bValue = b.model.split('/')[1] || '';
      }

      if (sortConfig.key === 'est_cost') {
        aValue = calculateEstimatedCost(a.metadata) || 0;
        bValue = calculateEstimatedCost(b.metadata) || 0;
      }

      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortConfig.direction === 'asc'
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }

      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc'
          ? aValue - bValue
          : bValue - aValue;
      }

      return 0;
    });
  }, [notebooks, sortConfig, selectedDandiset, qualResults, rankResults, vetoResults]);

  return (
    <div>
      <Typography variant="h4" gutterBottom>
        DANDI AI Notebooks Explorer
      </Typography>

      <FormControl sx={{ minWidth: 200, mb: 2 }}>
        <InputLabel id="dandiset-select-label">Filter by Dandiset ID</InputLabel>
        <Select
          labelId="dandiset-select-label"
          value={selectedDandiset}
          label="Filter by Dandiset ID"
          onChange={(e) => setSelectedDandiset(e.target.value)}
        >
          <MenuItem value="">
            <em>All Dandisets</em>
          </MenuItem>
          {uniqueDandisets.map((id) => (
            <MenuItem key={id} value={id}>{id}</MenuItem>
          ))}
        </Select>
      </FormControl>

      <Button
        variant="contained"
        sx={{ mb: 2, ml: 2 }}
        onClick={() => {
          // Convert data to CSV
          const headers = ['Notebook', 'Subfolder', 'Dandiset', 'Model', 'Prompt', 'Est. Cost', 'Qual', 'Rank', 'Human Veto'];
          const rows = filteredAndSortedNotebooks.map(notebook => {
            const notebookKey = `${notebook.dandiset_id}/${notebook.version}/${notebook.subfolder}`;
            const isQual = qualResults.get(notebookKey) ? '✓' : '✗';
            const rank = rankResults.get(notebookKey);
            const vetoes = vetoResults.get(notebookKey);
            const vetoText = vetoes?.length ? '✗' : '';

            return [
              notebook.dandiset_id + '.ipynb',
              notebook.subfolder,
              notebook.dandiset_id,
              notebook.model.split('/')[1] || notebook.model,
              notebook.prompt,
              calculateEstimatedCost(notebook.metadata)?.toFixed(2) || 'N/A',
              isQual,
              rank || '',
              vetoText
            ].join(',');
          });

          const csvContent = [headers.join(','), ...rows].join('\n');
          const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
          const link = document.createElement('a');
          link.href = URL.createObjectURL(blob);
          link.download = 'notebooks.csv';
          link.click();
        }}
      >
        Download as CSV
      </Button>

      <TableContainer component={Paper}>
        <Table sx={{ minWidth: 650 }}>
          <TableHead>
            <TableRow>
              <TableCell>Notebook</TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortConfig.key === 'subfolder'}
                  direction={sortConfig.key === 'subfolder' ? sortConfig.direction : 'asc'}
                  onClick={() => handleSort('subfolder')}
                >
                  Subfolder
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortConfig.key === 'dandiset_id'}
                  direction={sortConfig.key === 'dandiset_id' ? sortConfig.direction : 'asc'}
                  onClick={() => handleSort('dandiset_id')}
                >
                  Dandiset
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortConfig.key === 'model'}
                  direction={sortConfig.key === 'model' ? sortConfig.direction : 'asc'}
                  onClick={() => handleSort('model')}
                >
                  Model
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortConfig.key === 'prompt'}
                  direction={sortConfig.key === 'prompt' ? sortConfig.direction : 'asc'}
                  onClick={() => handleSort('prompt')}
                >
                  Prompt
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortConfig.key === 'est_cost'}
                  direction={sortConfig.key === 'est_cost' ? sortConfig.direction : 'asc'}
                  onClick={() => handleSort('est_cost')}
                >
                  Est. Cost ($)
                </TableSortLabel>
              </TableCell>
              {/* <TableCell>Critiques</TableCell> */}
              {/* <TableCell>
                <TableSortLabel
                  active={sortConfig.key === 'grade'}
                  direction={sortConfig.key === 'grade' ? sortConfig.direction : 'asc'}
                  onClick={() => handleSort('grade')}
                >
                  Grade
                </TableSortLabel>
              </TableCell> */}
              <TableCell>
                <TableSortLabel
                  active={sortConfig.key === 'qual'}
                  direction={sortConfig.key === 'qual' ? sortConfig.direction : 'asc'}
                  onClick={() => handleSort('qual')}
                >
                  Qual
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortConfig.key === 'rank'}
                  direction={sortConfig.key === 'rank' ? sortConfig.direction : 'asc'}
                  onClick={() => handleSort('rank')}
                >
                  Rank
                </TableSortLabel>
              </TableCell>
              <TableCell>
                <TableSortLabel
                  active={sortConfig.key === 'vetoes'}
                  direction={sortConfig.key === 'vetoes' ? sortConfig.direction : 'asc'}
                  onClick={() => handleSort('vetoes')}
                >
                  Human Veto
                </TableSortLabel>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredAndSortedNotebooks.map((notebook, index) => {
              // const critiqueUrls = getCritiqueUrls(notebook);
              const notebookKey = `${notebook.dandiset_id}/${notebook.version}/${notebook.subfolder}`;
              const isBestNonVetoed = bestNonVetoedNotebooks.get(notebook.dandiset_id) === notebookKey;
              return (
                <TableRow
                  key={index}
                  sx={isBestNonVetoed ? { backgroundColor: 'rgba(76, 175, 80, 0.1)' } : undefined}
                >
                  <TableCell>
                    <Link
                      href={notebook.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {notebook.dandiset_id}.ipynb
                    </Link>
                  </TableCell>
                  <TableCell>{notebook.subfolder}</TableCell>
                  <TableCell>{notebook.dandiset_id}</TableCell>
                  <TableCell>
                    {notebook.model.split('/')[1] || notebook.model}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={getPromptUrl(notebook.prompt)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {notebook.prompt}
                    </Link>
                  </TableCell>
                  <TableCell>
                    {calculateEstimatedCost(notebook.metadata)?.toFixed(2) || 'N/A'}
                  </TableCell>
                  {/* <TableCell>
                    {critiqueUrls.cells && (
                      <Link
                        href={critiqueUrls.cells}
                        target="_blank"
                        rel="noopener noreferrer"
                        sx={{ mr: 2 }}
                      >
                        Cells
                      </Link>
                    )}
                    {critiqueUrls.summary && (
                      <Link
                        href={critiqueUrls.summary}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Summary
                      </Link>
                    )}
                  </TableCell> */}
                  {/* <TableCell>
                    {(() => {
                      const grading = getNotebookGrade(notebook);
                      if (!grading) return null;
                      return (
                        <Link
                          href={grading.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          title={grading.thinking}
                          sx={{ cursor: 'pointer' }}
                        >
                          {grading.total}
                        </Link>
                      );
                    })()}
                  </TableCell> */}
                  <TableCell>
                    {qualResults.get(`${notebook.dandiset_id}/${notebook.version}/${notebook.subfolder}`) !== undefined ? (
                      <Link
                        href={`https://github.com/dandi-ai-notebooks/dandi-ai-notebooks-4/blob/main/reviews/${modelForReviews}/dandisets/${notebook.dandiset_id}/${notebook.version}/${notebook.subfolder}/qualification_test_thinking.md`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        {qualResults.get(`${notebook.dandiset_id}/${notebook.version}/${notebook.subfolder}`) ? (
                          <Typography component="span" sx={{ color: 'success.main' }}>✓</Typography>
                        ) : '✗'}
                      </Link>
                    ) : null}
                  </TableCell>
                  <TableCell>
                    <Link
                      href={`https://github.com/dandi-ai-notebooks/dandi-ai-notebooks-4/blob/main/reviews/${modelForReviews}/dandisets/${notebook.dandiset_id}/${notebook.version}/comparisons.md`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {rankResults.get(`${notebook.dandiset_id}/${notebook.version}/${notebook.subfolder}`)}
                    </Link>
                  </TableCell>
                  <TableCell>
                    {(() => {
                      const vetoes = vetoResults.get(`${notebook.dandiset_id}/${notebook.version}/${notebook.subfolder}`);
                      if (!vetoes?.length) return null;
                      return (
                        <Tooltip
                          title={
                            <div>
                              {vetoes.map((veto, i) => (
                                <div key={i}>
                                  <strong>{veto.user}:</strong>
                                  <br />
                                  {veto.reason}
                                  {i < vetoes.length - 1 && <hr />}
                                </div>
                              ))}
                            </div>
                          }
                        >
                          <Typography sx={{ color: 'error.main' }}>✗</Typography>
                        </Tooltip>
                      );
                    })()}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  );
}

const calculateEstimatedCost = (metadata: Metadata) => {
  const getModelCost = (model: string): [number | undefined, number | undefined] => {
    if (model === 'google/gemini-2.0-flash-001') return [0.1, 0.4];
    else if (model === 'google/gemini-2.5-flash-preview') return [0.15, 0.6];
    else if (model === 'google/gemini-2.5-pro-preview-03-25') return [1.25, 10];
    else if (model === 'google/gemini-2.5-pro-preview') return [1.25, 10];
    else if (model === 'openai/gpt-4o') return [2.5, 10];
    else if (model === 'anthropic/claude-3.5-sonnet') return [3, 15];
    else if (model === 'anthropic/claude-3.7-sonnet') return [3, 15];
    else if (model === 'anthropic/claude-3.7-sonnet:thinking') return [3, 15];
    else if (model === 'deepseek/deepseek-r1') return [0.55, 2.19];
    else if (model === 'deepseek/deepseek-chat-v3-0324') return [0.27, 1.1];
    else if (model === 'openai/o4-mini') return [1.1, 4.4];
    else if (model === 'openai/o4-mini-high') return [1.1, 4.4];
    else if (model === 'openai/gpt-4.1') return [2, 8];
    else if (model === 'openai/o3') return [10, 40];
    return [undefined, undefined];
  };

  if (!metadata) return 0;

  const [promptCost, completionCost] = getModelCost(metadata.model);
  if (promptCost === undefined || completionCost === undefined) return undefined;
  if (!metadata) return undefined;
  const totalPromptTokens = (metadata.total_prompt_tokens || 0) + (metadata.total_vision_prompt_tokens || 0);
  const totalCompletionTokens = (metadata.total_completion_tokens || 0) + (metadata.total_vision_completion_tokens || 0);

  return ((totalPromptTokens / 1e6 * promptCost) + (totalCompletionTokens / 1e6 * completionCost));
};
