// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title OracleCard
 * @notice Minimal self-contained ERC-721 for Hermes Oracle tarot readings.
 *         Each token represents one card from a reading; metadata + image
 *         live on IPFS via Pinata. Mint is restricted to the deployer.
 *
 * Single-file (no external imports) so the project ships without npm/foundry.
 * Implements: ERC721 + ERC721Metadata + ERC165 (the surface OpenSea expects).
 * Notably omitted: ERC721Enumerable (not needed; saves gas).
 */

interface IERC165 {
    function supportsInterface(bytes4 interfaceId) external view returns (bool);
}

interface IERC721 {
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);
    event Approval(address indexed owner, address indexed approved, uint256 indexed tokenId);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);

    function balanceOf(address owner) external view returns (uint256);
    function ownerOf(uint256 tokenId) external view returns (address);
    function safeTransferFrom(address from, address to, uint256 tokenId) external;
    function safeTransferFrom(address from, address to, uint256 tokenId, bytes calldata data) external;
    function transferFrom(address from, address to, uint256 tokenId) external;
    function approve(address to, uint256 tokenId) external;
    function setApprovalForAll(address operator, bool approved) external;
    function getApproved(uint256 tokenId) external view returns (address);
    function isApprovedForAll(address owner, address operator) external view returns (bool);
}

interface IERC721Metadata is IERC721 {
    function name() external view returns (string memory);
    function symbol() external view returns (string memory);
    function tokenURI(uint256 tokenId) external view returns (string memory);
}

interface IERC721Receiver {
    function onERC721Received(address operator, address from, uint256 tokenId, bytes calldata data)
        external returns (bytes4);
}

contract OracleCard is IERC721, IERC721Metadata, IERC165 {
    string private _name;
    string private _symbol;
    address public owner;
    uint256 public totalSupply;

    mapping(uint256 => address) private _owners;
    mapping(address => uint256) private _balances;
    mapping(uint256 => address) private _tokenApprovals;
    mapping(address => mapping(address => bool)) private _operatorApprovals;
    mapping(uint256 => string) private _tokenURIs;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    event CardMinted(address indexed to, uint256 indexed tokenId, string tokenURI);

    constructor(string memory name_, string memory symbol_) {
        _name = name_;
        _symbol = symbol_;
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero owner");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    // ---------- ERC721Metadata ----------

    function name() external view returns (string memory) { return _name; }
    function symbol() external view returns (string memory) { return _symbol; }

    function tokenURI(uint256 tokenId) external view returns (string memory) {
        require(_owners[tokenId] != address(0), "nonexistent");
        return _tokenURIs[tokenId];
    }

    // ---------- ERC165 ----------

    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        return
            interfaceId == type(IERC721).interfaceId ||
            interfaceId == type(IERC721Metadata).interfaceId ||
            interfaceId == type(IERC165).interfaceId;
    }

    // ---------- ERC721 ----------

    function balanceOf(address owner_) external view returns (uint256) {
        require(owner_ != address(0), "zero addr");
        return _balances[owner_];
    }

    function ownerOf(uint256 tokenId) public view returns (address) {
        address o = _owners[tokenId];
        require(o != address(0), "nonexistent");
        return o;
    }

    function approve(address to, uint256 tokenId) external {
        address tokenOwner = ownerOf(tokenId);
        require(to != tokenOwner, "approve to current owner");
        require(msg.sender == tokenOwner || _operatorApprovals[tokenOwner][msg.sender], "not authorized");
        _tokenApprovals[tokenId] = to;
        emit Approval(tokenOwner, to, tokenId);
    }

    function getApproved(uint256 tokenId) external view returns (address) {
        require(_owners[tokenId] != address(0), "nonexistent");
        return _tokenApprovals[tokenId];
    }

    function setApprovalForAll(address operator, bool approved) external {
        require(operator != msg.sender, "approve to caller");
        _operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    function isApprovedForAll(address owner_, address operator) external view returns (bool) {
        return _operatorApprovals[owner_][operator];
    }

    function transferFrom(address from, address to, uint256 tokenId) public {
        require(_isApprovedOrOwner(msg.sender, tokenId), "not authorized");
        _transfer(from, to, tokenId);
    }

    function safeTransferFrom(address from, address to, uint256 tokenId) external {
        safeTransferFrom(from, to, tokenId, "");
    }

    function safeTransferFrom(address from, address to, uint256 tokenId, bytes memory data) public {
        transferFrom(from, to, tokenId);
        require(_checkOnERC721Received(from, to, tokenId, data), "non-ERC721Receiver");
    }

    // ---------- Mint ----------

    /// @notice Mint a new oracle card to `to` with metadata URI pointing to IPFS.
    /// @return tokenId The newly-minted token id.
    function safeMint(address to, string calldata uri) external onlyOwner returns (uint256) {
        require(to != address(0), "zero to");
        uint256 tokenId = ++totalSupply; // 1-indexed
        _owners[tokenId] = to;
        _balances[to] += 1;
        _tokenURIs[tokenId] = uri;
        emit Transfer(address(0), to, tokenId);
        emit CardMinted(to, tokenId, uri);
        require(_checkOnERC721Received(address(0), to, tokenId, ""), "non-ERC721Receiver");
        return tokenId;
    }

    // ---------- Internals ----------

    function _isApprovedOrOwner(address spender, uint256 tokenId) internal view returns (bool) {
        address tokenOwner = ownerOf(tokenId);
        return spender == tokenOwner ||
               _tokenApprovals[tokenId] == spender ||
               _operatorApprovals[tokenOwner][spender];
    }

    function _transfer(address from, address to, uint256 tokenId) internal {
        require(ownerOf(tokenId) == from, "wrong from");
        require(to != address(0), "zero to");
        delete _tokenApprovals[tokenId];
        _balances[from] -= 1;
        _balances[to] += 1;
        _owners[tokenId] = to;
        emit Transfer(from, to, tokenId);
    }

    function _checkOnERC721Received(address from, address to, uint256 tokenId, bytes memory data)
        private returns (bool)
    {
        // EOAs always accept.
        if (to.code.length == 0) return true;
        try IERC721Receiver(to).onERC721Received(msg.sender, from, tokenId, data) returns (bytes4 ret) {
            return ret == IERC721Receiver.onERC721Received.selector;
        } catch {
            return false;
        }
    }
}
