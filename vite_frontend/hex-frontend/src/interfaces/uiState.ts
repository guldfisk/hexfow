import { CC } from "./geometry.ts";
import { Hex } from "./gameState.ts";

export interface HexDecoration {
  overlay: boolean;
  selectionIcon: string | null;
}

abstract class UIMenu {
  abstract hexClicked(hex: Hex): null;
  abstract hexHovered(hex: Hex): null;
  abstract getHexDecorations(): { [hexCC: string]: HexDecoration };
}

class SelectConsecutiveAdjacentHexesMenu extends UIMenu {
  adjacentTo: CC;
  armLength: number;
  hoveringOn: CC | null;

  constructor(adjacentTo: CC, armLength: number) {
    super();
    this.adjacentTo = adjacentTo;
    this.armLength = armLength;
  }

  getHexDecorations(): { [p: string]: HexDecoration } {
    return {};
  }

  hexClicked(hex: Hex): null {
    return null;
  }

  hexHovered(hex: Hex): null {
    return null;
  }
}

export interface selectConsecutiveAdjacentHexes {
  adjacentTo: CC;
  armLength: number;
  hoveringOn: CC | null;
}

export type uiState = selectConsecutiveAdjacentHexes | null;
