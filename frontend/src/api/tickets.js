import axios from 'axios';

export async function fetchCompleteTickets() {
  const { data } = await axios.get('/api/complete-tickets');
  return data.tickets;
}

export async function fetchIncompleteTickets() {
  const { data } = await axios.get('/api/incomplete-tickets');
  return data.tickets;
}

export async function generateSolutions(ticketKey) {
  const { data } = await axios.post(`/api/generate-solutions/${ticketKey}`);
  return data.solutions;
}

export async function postSolution(ticketKey, solution) {
  return axios.post(`/api/post-solution/${ticketKey}`, solution);
}

export async function getNextPollEta() {
  const { data } = await axios.get('/api/next-poll-eta');
  return data.next_poll_eta;
}
