import "./style.css";
import { createRoot } from "react-dom/client";
import { useState } from "react";

interface Seat {
  id: string;
  position: number;
  player_name: string;
}
interface GameResponse {
  seats: Seat[];
}

const SeatRow = ({ seat }: { seat: Seat }) => {
  const [copied, setCopied] = useState(false);
  const link = `${window.location.protocol + "//" + window.location.host}/play/?seat=${seat.id}`;

  return (
    <tr>
      <td>{seat.player_name}</td>
      <td>
        <a href={link}>join</a>
      </td>
      <td>
        <button
          onClick={() => {
            setCopied(true);
            navigator.clipboard.writeText(link);
          }}
        >
          {copied ? "copied" : "copy"}
        </button>
      </td>
    </tr>
  );
};

const GameCreator = ({}: {}) => {
  const [loading, setLoading] = useState(false);
  const [game, setGame] = useState<GameResponse | null>(null);

  if (game) {
    return (
      <div className={"game-result"}>
        <table>
          {game.seats.map((seat) => (
            <SeatRow seat={seat} />
          ))}
        </table>
      </div>
    );
  }

  return (
    <div>
      <button
        className={"big-button"}
        onClick={() => {
          setLoading(true);
          fetch(
            `${window.location.protocol + "//" + window.location.hostname}:8000/create-game`,
            {
              method: "POST",
              body: JSON.stringify({ game_type: "tutorial" }),
              headers: {
                "Content-type": "application/json",
              },
            },
          )
            .then((response) => response.json())
            .then(setGame);
        }}
        disabled={loading}
      >
        Create game
      </button>
    </div>
  );
};

createRoot(document.getElementById("root")!).render(<GameCreator />);
