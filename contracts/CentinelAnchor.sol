// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title CentinelAnchor
/// @notice Contrato mínimo para anclar Merkle roots.
contract CentinelAnchor {
    event HashRootAnchored(bytes32 indexed root, uint256 timestamp);

    /// @notice Emite un evento con el Merkle root anclado.
    /// @param root Merkle root keccak256.
    function anchor(bytes32 root) external {
        emit HashRootAnchored(root, block.timestamp);
    }
}
