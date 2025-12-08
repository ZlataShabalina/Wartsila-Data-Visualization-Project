
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import Homepage from './assets/components/Homepage';
import Graph from './assets/components/Graph';
import 'bootstrap/dist/css/bootstrap.css';
import 'bootstrap';

function App() {
  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Homepage />} />
          <Route path="/graph" element={<Graph />} />
        </Routes>
      </BrowserRouter>
    </>
  );
}

export default App;
