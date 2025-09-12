import {GameState, Hex} from "../interfaces/gameState.ts";
import {GameObjectDetails} from "../interfaces/gameObjectDetails.ts";
import {traverseStatuses} from "./statuses.ts";
import {getImageUrl} from "../image/images.ts";
import {StatusDetailView} from "./statusDetails.tsx";
import React from "react";

export const HexDetailView = ({
  hex,
  //   TODO handle this in a non trash way
  gameObjectDetails,
  gameState,
}: {
  hex: Hex;
  gameObjectDetails: GameObjectDetails;
  gameState: GameState;
}) => {
  const terrainDetails = gameObjectDetails.terrain[hex.terrain];
  const relatedStatuses: string[] = [];
  for (const status of terrainDetails.related_statuses) {
    if (!relatedStatuses.includes(status)) {
      relatedStatuses.push(status);
      traverseStatuses(status, gameObjectDetails, relatedStatuses);
    }
  }
  return (
    <div>
      <div
        style={{
          fontSize: "18px",
        }}
      >
        {terrainDetails.name}
      </div>
      <img
        src={getImageUrl("terrain", hex.terrain)}
        className={"terrain-image"}
      />
      <div className={"facet-details"}>
        {hex.visible
          ? "visible"
          : "not visible" +
            (hex.last_visible_round !== null &&
            gameState.round - hex.last_visible_round > 0
              ? ` - last visible ${gameState.round - hex.last_visible_round} rounds ago`
              : "")}
      </div>
      {terrainDetails.is_water ||
      terrainDetails.blocks_vision ||
      terrainDetails.is_high_ground ? (
        <div className={"facet-details"}>
          {terrainDetails.blocks_vision ? <div>Blocks vision</div> : null}
          {terrainDetails.is_water ? <div>Water</div> : null}
          {terrainDetails.is_high_ground ? <div>High ground</div> : null}
        </div>
      ) : null}
      {terrainDetails.description ? (
        <div className={"facet-details"}>{terrainDetails.description}</div>
      ) : null}

      {relatedStatuses.map((statusIdentifier) => (
        <StatusDetailView
          status={null}
          statusDetails={gameObjectDetails.statuses[statusIdentifier]}
        />
      ))}
    </div>
  );
};