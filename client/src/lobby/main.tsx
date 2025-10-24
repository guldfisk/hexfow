import "./style.css";
import { createRoot } from "react-dom/client";
import { StrictMode, useEffect, useState } from "react";
import { useLobbyDispatch, useLobbyState } from "./state/hooks.ts";
import { Provider } from "react-redux";
import {
  GameType,
  Seat,
  setGameResponse,
  setMapNames,
  setSelectedGameType,
  setSettings,
  setWithCustomArmies,
  setWithFow,
  store,
} from "./state/store.ts";

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

const GameTypeSelector = ({}) => {
  const gameType = useLobbyState((state) => state.selectedGameType);
  const dispatch = useLobbyDispatch();
  return (
    <div>
      <label>Game type</label>
      <select
        value={gameType}
        onChange={(value) =>
          dispatch(setSelectedGameType(value.target.value as GameType))
        }
      >
        {["random", "map"].map((name) => (
          <option value={name}>{name}</option>
        ))}
      </select>
    </div>
  );
};

const SettingsSelector = ({}) => {
  const gameType = useLobbyState((state) => state.selectedGameType);
  const settings = useLobbyState((state) => state.settings);
  const mapNames = useLobbyState((state) => state.mapNames);
  const dispatch = useLobbyDispatch();

  if (gameType == "map" && settings.map_name) {
    return (
      <div>
        <label>Map</label>
        <select
          value={settings.map_name}
          onChange={(value) =>
            dispatch(setSettings({ map_name: value.target.value }))
          }
        >
          {mapNames.map((name) => (
            <option value={name}>{name}</option>
          ))}
        </select>
      </div>
    );
  }
};

const GameCreator = ({}: {}) => {
  const [loading, setLoading] = useState(false);
  const gameType = useLobbyState((state) => state.selectedGameType);
  const withFow = useLobbyState((state) => state.withFow);
  const withCustomArmies = useLobbyState((state) => state.withCustomArmies);
  const settings = useLobbyState((state) => state.settings);
  const gameResponse = useLobbyState((state) => state.gameResponse);
  const dispatch = useLobbyDispatch();

  const [useChessClock, setUseChessClock] = useState(true);
  const [timeBank, setTimeBank] = useState(30);
  const [grace, setGrace] = useState(2);

  useEffect(() => {
    fetch(
      `${window.location.protocol + "//" + window.location.hostname}:8000/maps`,
    ).then(async (response) => {
      dispatch(setMapNames((await response.json()).map((map) => map.name)));
    });
    return () => {};
  }, []);

  if (gameResponse) {
    return (
      <div className={"game-result"}>
        <table>
          {gameResponse.seats.map((seat) => (
            <SeatRow seat={seat} />
          ))}
        </table>
      </div>
    );
  }

  return (
    <div className={"creation-menu"}>
      <button
        className={"big-button"}
        onClick={() => {
          setLoading(true);
          fetch(
            `${window.location.protocol + "//" + window.location.hostname}:8000/create-game`,
            {
              method: "POST",
              body: JSON.stringify({
                game_type: gameType,
                settings: settings,
                with_fow: withFow,
                custom_armies: withCustomArmies,
                time_bank: useChessClock ? timeBank * 60 : null,
                time_grace: useChessClock ? grace : null,
              }),
              headers: {
                "Content-type": "application/json",
              },
            },
          )
            .then((response) => response.json())
            .then((response) => dispatch(setGameResponse(response)));
        }}
        disabled={loading}
      >
        Create game
      </button>
      <div>
        <label>With FOW</label>
        <input
          type={"checkbox"}
          checked={withFow}
          onChange={() => dispatch(setWithFow(!withFow))}
        />
      </div>
      <div>
        <label>With custom armies</label>
        <input
          type={"checkbox"}
          checked={withCustomArmies}
          onChange={() => dispatch(setWithCustomArmies(!withCustomArmies))}
        />
      </div>
      <div>
        <label>Use chess clock</label>
        <input
          type={"checkbox"}
          checked={useChessClock}
          onChange={() => setUseChessClock((prev) => !prev)}
        />
      </div>
      <div>
        <label>Time bank minutes</label>
        <input
          type={"number"}
          value={timeBank}
          onChange={(event) => setTimeBank(parseInt(event.target.value))}
        />
      </div>
      <div>
        <label>Time grace seconds</label>
        <input
          type={"number"}
          value={grace}
          onChange={(event) => setGrace(parseInt(event.target.value))}
        />
      </div>
      <GameTypeSelector />
      <SettingsSelector />
    </div>
  );
};

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <GameCreator />
    </Provider>
  </StrictMode>,
);
